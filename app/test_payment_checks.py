import gc
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import server


class PaymentChecksTest(unittest.TestCase):
    def setUp(self):
        self.original_db_path = server.DB_PATH
        self.path = Path(__file__).parent / "test_data" / f"payment-checks-{uuid.uuid4().hex}.db"
        server.DB_PATH = self.path
        server.ensure_app_db()
        self.started = datetime(2026, 10, 9, 9, tzinfo=timezone.utc)
        self.env = patch.object(server, "yookassa_env", return_value=("shop", "secret", "url"))
        self.env.start()

    def tearDown(self):
        self.env.stop()
        server.DB_PATH = self.original_db_path
        gc.collect()
        for suffix in ("", "-wal", "-shm"):
            Path(f"{self.path}{suffix}").unlink(missing_ok=True)

    def create_order(self):
        with patch.object(server, "now_iso", return_value=self.started.isoformat()), patch.object(
            server, "create_yookassa_payment",
            return_value={"id": "payment-test", "confirmation": {"confirmation_url": "https://pay.test"}},
        ):
            server.create_product_payment({"email": "buyer@example.test", "products": ["participle-map", "syntactic-soup"]})
        with server.db() as con:
            return con.execute("SELECT order_uid FROM shop_orders ORDER BY id DESC LIMIT 1").fetchone()[0]

    def payment(self, uid, status):
        return {"id": "payment-test", "status": status, "amount": {"value": "900.00", "currency": "RUB"}, "metadata": {"order_uid": uid, "product_id": "participle_map"}}

    def check_at(self, minutes=0, seconds=0):
        stamp = (self.started + timedelta(minutes=minutes, seconds=seconds)).isoformat()
        with patch.object(server, "now_iso", return_value=stamp):
            server.check_pending_order_payments(stamp)

    def order(self, uid):
        with server.db() as con:
            return dict(con.execute("SELECT * FROM shop_orders WHERE order_uid = ?", (uid,)).fetchone())

    def test_checks_continue_after_first_three_and_survive_db_reinitialization(self):
        uid = self.create_order()
        with patch.object(server, "get_yookassa_payment", return_value=self.payment(uid, "pending")) as api, patch.object(
            server, "send_order_email"
        ) as mail:
            self.check_at(2, 59)
            self.assertEqual(api.call_count, 0)
            self.check_at(3)
            self.check_at(3)
            self.check_at(9, 59)
            self.assertEqual(api.call_count, 1)
            server.ensure_app_db()
            self.check_at(10)
            self.check_at(14, 59)
            self.assertEqual(api.call_count, 2)
            self.check_at(15)
            self.check_at(60)
            self.assertEqual(api.call_count, 3)
            self.check_at(75)
            self.assertEqual(api.call_count, 4)
            mail.assert_not_called()
        self.assertEqual(self.order(uid)["payment_check_count"], 4)

    def test_success_sends_all_materials_without_browser_return(self):
        uid = self.create_order()
        with patch.object(server, "get_yookassa_payment", return_value=self.payment(uid, "succeeded")), patch.object(
            server, "send_order_email"
        ) as mail:
            self.check_at(3)
            self.check_at(10)
            self.check_at(15)
            mail.assert_called_once()
            self.assertEqual(len(mail.call_args.args[1]), 2)
        self.assertEqual(self.order(uid)["status"], "paid")
        self.assertEqual(self.order(uid)["email_sent"], 1)

    def test_canceled_stops_checks(self):
        uid = self.create_order()
        with patch.object(server, "get_yookassa_payment", return_value=self.payment(uid, "canceled")) as api, patch.object(
            server, "send_order_email"
        ) as mail:
            self.check_at(3)
            self.check_at(10)
            self.check_at(15)
            api.assert_called_once()
            mail.assert_not_called()
        self.assertEqual(self.order(uid)["status"], "canceled")

    def test_network_failure_keeps_later_checks(self):
        uid = self.create_order()
        with patch.object(server, "get_yookassa_payment", side_effect=[RuntimeError("offline"), self.payment(uid, "succeeded")]), patch.object(
            server, "send_order_email"
        ) as mail:
            self.check_at(3)
            self.assertEqual(self.order(uid)["payment_check_count"], 1)
            self.check_at(10)
            mail.assert_called_once()

    def test_mail_failure_retries_paid_order_at_next_slot(self):
        uid = self.create_order()
        with patch.object(server, "get_yookassa_payment", return_value=self.payment(uid, "succeeded")), patch.object(
            server, "send_order_email", side_effect=[server.MailDeliveryError("SMTP unavailable"), None]
        ) as mail:
            self.check_at(3)
            self.assertEqual(self.order(uid)["status"], "paid")
            self.assertEqual(self.order(uid)["email_sent"], 0)
            self.check_at(10)
            self.check_at(15)
            self.assertEqual(mail.call_count, 2)
        self.assertEqual(self.order(uid)["email_sent"], 1)

    def test_webhook_return_and_worker_send_only_one_email(self):
        uid = self.create_order()
        payment = self.payment(uid, "succeeded")
        webhook = {"event": "payment.succeeded", "object": payment}
        with patch.object(server, "get_yookassa_payment", return_value=payment), patch.object(server, "send_order_email") as mail:
            with ThreadPoolExecutor(max_workers=3) as pool:
                futures = [
                    pool.submit(self.check_at, 3),
                    pool.submit(server.process_yookassa_webhook, webhook, "{}"),
                    pool.submit(server.confirm_order_return, {"order_uid": uid}),
                ]
                for future in futures:
                    future.result(timeout=10)
            mail.assert_called_once()

    def test_existing_pending_orders_use_creation_time_and_catch_up(self):
        uid = self.create_order()
        with server.db() as con:
            con.execute("UPDATE shop_orders SET payment_check_started_at = NULL WHERE order_uid = ?", (uid,))
        with patch.object(server, "get_yookassa_payment", return_value=self.payment(uid, "succeeded")), patch.object(server, "send_order_email") as mail:
            self.check_at(60)
            mail.assert_called_once()

    def test_wrong_payment_metadata_never_sends_materials(self):
        uid = self.create_order()
        with patch.object(server, "get_yookassa_payment", return_value=self.payment("wrong-order", "succeeded")), patch.object(server, "send_order_email") as mail:
            self.check_at(3)
            mail.assert_not_called()
        self.assertEqual(self.order(uid)["status"], "pending")

    def test_failed_order_does_not_block_other_orders(self):
        first = self.create_order()
        second = self.create_order()
        with patch.object(server, "get_yookassa_payment", side_effect=[RuntimeError("offline"), self.payment(second, "succeeded")]), patch.object(server, "send_order_email") as mail:
            self.check_at(3)
            mail.assert_called_once()
        self.assertEqual(self.order(first)["status"], "pending")
        self.assertEqual(self.order(second)["email_sent"], 1)

    def test_orders_without_payment_id_or_with_final_status_are_ignored(self):
        uid = self.create_order()
        with patch.object(server, "get_yookassa_payment") as api:
            for changes in (
                "yookassa_payment_id = NULL",
                "yookassa_payment_id = 'payment-test', status = 'payment_error'",
                "status = 'canceled'",
                "status = 'paid', email_sent = 1",
            ):
                with server.db() as con:
                    con.execute(f"UPDATE shop_orders SET {changes} WHERE order_uid = ?", (uid,))
                self.check_at(15)
            api.assert_not_called()

    def test_worker_checks_immediately_and_stops_after_signal(self):
        stop = server.threading.Event()
        with patch.object(server, "check_pending_order_payments", side_effect=lambda: stop.set()) as check:
            server.payment_check_worker(stop)
            check.assert_called_once()


if __name__ == "__main__":
    unittest.main()
