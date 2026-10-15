import sqlite3
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from email.message import EmailMessage
from unittest.mock import Mock, patch

import server
import test_payment_checks as fixtures


class DeliveryReliabilityTest(unittest.TestCase):
    setUp = fixtures.PaymentChecksTest.setUp
    tearDown = fixtures.PaymentChecksTest.tearDown
    create_order = fixtures.PaymentChecksTest.create_order
    order = fixtures.PaymentChecksTest.order
    payment = fixtures.PaymentChecksTest.payment
    check_at = fixtures.PaymentChecksTest.check_at
    admin = {'role': 'admin', 'user_id': 'test-admin'}

    def paid(self):
        uid = self.create_order()
        with server.db() as con:
            con.execute("UPDATE shop_orders SET status = 'paid', payment_verified_id = yookassa_payment_id WHERE order_uid = ?", (uid,))
        return uid

    def test_paid_retry_never_calls_gateway_or_creates_payment(self):
        uid = self.paid()
        with patch.object(server, 'get_yookassa_payment') as api, patch.object(server, 'create_yookassa_payment') as create, patch.object(server, 'send_order_email') as mail:
            server.deliver_product_order(uid, 'payment-test')
            server.deliver_product_order(uid, 'payment-test')
            mail.assert_called_once()
            api.assert_not_called()
            create.assert_not_called()

    def test_admin_retry_verifies_unverified_paid_order_and_sends_once(self):
        uid = self.create_order()
        with server.db() as con:
            con.execute("UPDATE shop_orders SET status = 'paid' WHERE order_uid = ?", (uid,))
        with patch.object(server, 'get_yookassa_payment', return_value=self.payment(uid, 'succeeded')) as api, patch.object(server, 'send_order_email') as mail:
            server.admin_order_delivery(self.admin, {'order_uid': uid, 'action': 'retry', 'confirmed': True})
            api.assert_called_once()
            mail.assert_called_once()

    def test_single_product_delivery(self):
        with patch.object(server, 'create_yookassa_payment', return_value={'id': 'single', 'confirmation': {'confirmation_url': 'https://pay.test'}}):
            server.create_product_payment({'email': 'buyer@example.test', 'products': ['syntactic-soup']})
        with server.db() as con:
            uid = con.execute('SELECT order_uid FROM shop_orders').fetchone()[0]
        payment = {'id': 'single', 'status': 'succeeded', 'amount': {'value': '300.00', 'currency': 'RUB'}, 'metadata': {'order_uid': uid, 'product_id': 'syntactic_soup'}}
        with patch.object(server, 'get_yookassa_payment', return_value=payment), patch.object(server, 'send_order_email') as mail:
            server.confirm_order_return({'order_uid': uid})
            self.assertEqual(len(mail.call_args.args[1]), 1)

    def test_retries_backoff_and_attention_after_five_failures(self):
        uid = self.paid()
        stamp = self.started
        with patch.object(server, 'send_order_email', side_effect=server.MailDeliveryError('network')) as mail:
            for count in range(1, 6):
                with patch.object(server, 'now_iso', return_value=stamp.isoformat()):
                    server.attempt_order_delivery(uid)
                    row = self.order(uid)
                    server.attempt_order_delivery(uid)
                    self.assertEqual(mail.call_count, count)
                if count < 5:
                    self.assertEqual(row['delivery_status'], 'retry')
                    stamp += timedelta(seconds=60 * 2 ** count)
            self.assertEqual(self.order(uid)['delivery_status'], 'attention')
        with patch.object(server, 'send_order_email') as mail:
            server.admin_order_delivery(self.admin, {'order_uid': uid, 'action': 'retry', 'confirmed': True})
            mail.assert_called_once()
        self.assertEqual(self.order(uid)['delivery_status'], 'sent')

    def test_ambiguous_send_blocks_webhook_worker_and_return(self):
        uid = self.paid()
        with patch.object(server, 'send_order_email', side_effect=server.MailDeliveryError('lost acknowledgement', True)) as mail:
            server.deliver_product_order(uid, 'payment-test')
            server.confirm_order_return({'order_uid': uid})
            server.process_yookassa_webhook({'event': 'payment.succeeded', 'object': self.payment(uid, 'succeeded')}, '{}')
            self.check_at(60)
            mail.assert_called_once()
        self.assertEqual(self.order(uid)['delivery_status'], 'unknown')

    def test_restart_after_smtp_acceptance_and_sqlite_failure_never_resends(self):
        uid = self.paid()
        with patch.object(server, 'send_order_email') as mail, patch.object(server, 'finish_delivery_attempt', side_effect=sqlite3.OperationalError('disk full')):
            with patch.object(server, 'now_iso', return_value=self.started.isoformat()), self.assertRaises(sqlite3.OperationalError):
                server.attempt_order_delivery(uid)
            mail.assert_called_once()
        server.ensure_app_db()
        with patch.object(server, 'send_order_email') as mail:
            self.check_at(6)
            server.confirm_order_return({'order_uid': uid})
            mail.assert_not_called()
        self.assertEqual(self.order(uid)['delivery_status'], 'unknown')
        history = server.admin_order_delivery(self.admin, {'order_uid': uid, 'action': 'history'})['history']
        self.assertEqual(history[0]['result'], 'unknown')

    def test_database_claim_works_without_process_locks(self):
        uid = self.paid()
        entered, release = threading.Event(), threading.Event()
        def send(*args):
            entered.set()
            self.assertTrue(release.wait(5))
        with patch.object(server, 'send_order_email', side_effect=send) as mail, ThreadPoolExecutor(2) as pool:
            first = pool.submit(server.attempt_order_delivery, uid)
            self.assertTrue(entered.wait(5))
            second = pool.submit(server.attempt_order_delivery, uid)
            try:
                self.assertEqual(second.result(timeout=5)['delivery_status'], 'sending')
            finally:
                release.set()
            first.result(timeout=5)
            mail.assert_called_once()

    def test_manual_confirmation_and_authorization(self):
        uid = self.paid()
        with server.db() as con:
            con.execute('UPDATE shop_orders SET receipt_sent = 1, receipt_note = ? WHERE order_uid = ?', ('receipt-note', uid))
        payload = {'order_uid': uid, 'action': 'manual', 'confirmed': True}
        with self.assertRaises(PermissionError):
            server.admin_order_delivery({'role': 'teacher'}, payload)
        with self.assertRaises(ValueError):
            server.admin_order_delivery(self.admin, {**payload, 'confirmed': False})
        server.admin_order_delivery(self.admin, payload)
        with patch.object(server, 'send_order_email') as mail:
            self.check_at(60)
            server.deliver_product_order(uid, 'payment-test')
            mail.assert_not_called()
        self.assertEqual(self.order(uid)['receipt_sent'], 1)
        self.assertEqual(self.order(uid)['receipt_note'], 'receipt-note')
        self.assertEqual(self.order(uid)['delivery_status'], 'manual')

    def test_snapshot_survives_catalog_edits(self):
        uid = self.paid()
        before = server.order_products(uid)
        with server.db() as con:
            con.execute("UPDATE paid_entities SET title = 'changed', delivery_url = 'https://changed.test' WHERE product_id = 'participle_map'")
        self.assertEqual(server.order_products(uid), before)
        with patch.object(server, 'send_order_email') as mail:
            server.attempt_order_delivery(uid)
            self.assertEqual(mail.call_args.args[1], before)

    def test_missing_or_invalid_link_stops_before_smtp(self):
        uid = self.paid()
        with server.db() as con:
            con.execute("UPDATE shop_order_items SET snapshot_json = replace(snapshot_json, 'http', 'file') WHERE order_uid = ?", (uid,))
        with patch.object(server, 'send_order_email') as mail:
            server.attempt_order_delivery(uid)
            mail.assert_not_called()
        self.assertEqual(self.order(uid)['delivery_status'], 'attention')

    def test_disable_persists_and_existing_payment_still_delivers(self):
        uid = self.create_order()
        server.admin_payment_availability(self.admin, {'enabled': False})
        server.ensure_app_db()
        self.assertFalse(server.shop_products_public()['payments_enabled'])
        with patch.object(server, 'create_yookassa_payment') as create:
            with self.assertRaises(RuntimeError):
                server.create_product_payment({'email': 'buyer@example.test'})
            create.assert_not_called()
        with patch.object(server, 'get_yookassa_payment', return_value=self.payment(uid, 'succeeded')), patch.object(server, 'send_order_email') as mail:
            server.process_yookassa_webhook({'event': 'payment.succeeded', 'object': self.payment(uid, 'succeeded')}, '{}')
            mail.assert_called_once()
        server.admin_payment_availability(self.admin, {'enabled': True})
        self.assertTrue(server.payments_enabled())

    def test_wrong_amount_product_or_payment_id_does_not_mark_paid(self):
        uid = self.create_order()
        for field, value in [('amount', {'value': '1.00', 'currency': 'RUB'}), ('id', 'wrong'), ('metadata', {'order_uid': uid, 'product_id': 'wrong'})]:
            payment = {**self.payment(uid, 'succeeded'), field: value}
            with patch.object(server, 'get_yookassa_payment', return_value=payment), patch.object(server, 'send_order_email') as mail:
                server.process_yookassa_webhook({'event': 'payment.succeeded', 'object': self.payment(uid, 'succeeded')}, '{}')
                mail.assert_not_called()
            self.assertEqual(self.order(uid)['status'], 'pending')

    def test_legacy_orders_are_held_and_flags_preserved(self):
        uid = self.paid()
        with server.db() as con:
            con.execute("UPDATE shop_orders SET delivery_status = 'legacy_review', payment_verified_id = NULL, receipt_sent = 1 WHERE order_uid = ?", (uid,))
            con.execute('UPDATE shop_order_items SET snapshot_json = NULL WHERE order_uid = ?', (uid,))
        server.ensure_app_db()
        with patch.object(server, 'get_yookassa_payment', return_value=self.payment(uid, 'succeeded')), patch.object(server, 'send_order_email') as mail:
            self.check_at(60)
            mail.assert_not_called()
            server.admin_order_delivery(self.admin, {'order_uid': uid, 'action': 'retry', 'confirmed': True})
            mail.assert_called_once()
        self.assertEqual(self.order(uid)['receipt_sent'], 1)

    def test_migration_from_real_old_columns_is_idempotent(self):
        uid = self.paid()
        with server.db() as con:
            con.execute("UPDATE shop_orders SET email_sent = 1, receipt_sent = 1, receipt_note = 'keep' WHERE order_uid = ?", (uid,))
            con.execute('DROP INDEX idx_delivery_due')
            con.execute('DROP INDEX idx_shop_orders_payment_checks_v2')
            for column in ('delivery_status', 'delivery_attempts', 'delivery_last_at', 'delivery_next_at', 'delivery_error', 'delivery_method', 'delivery_token', 'delivery_lease_at', 'payment_verified_id', 'payment_next_at'):
                con.execute(f'ALTER TABLE shop_orders DROP COLUMN {column}')
            con.execute('ALTER TABLE shop_order_items DROP COLUMN snapshot_json')
            con.execute('DROP TABLE shop_delivery_history')
            con.execute('DROP TABLE shop_settings')
        server.ensure_app_db()
        server.ensure_app_db()
        row = self.order(uid)
        self.assertEqual((row['status'], row['email_sent'], row['receipt_sent'], row['receipt_note'], row['delivery_status']), ('paid', 1, 1, 'keep', 'sent'))
        self.assertEqual(len(server.order_products(uid)), 2)

    def test_missing_local_file_is_detected(self):
        with self.assertRaises(ValueError):
            server.validate_delivery_link(server.APP_BASE_URL + '/full-games/participle-map/nonexistent.pdf')

    def test_recovery_preserves_fresh_lease_of_slow_preparation(self):
        uid = self.paid()
        with server.db() as con:
            con.execute("""UPDATE shop_orders SET delivery_status = 'sending', delivery_token = 'active',
                           delivery_last_at = ?, delivery_lease_at = ? WHERE order_uid = ?""",
                        (self.started.isoformat(), (self.started + timedelta(minutes=6)).isoformat(), uid))
        with patch.object(server, 'send_order_email') as mail:
            server.recover_and_deliver_orders((self.started + timedelta(minutes=7)).isoformat())
            mail.assert_not_called()
        self.assertEqual(self.order(uid)['delivery_status'], 'sending')

    def test_external_link_checks_are_bounded_and_reject_private_hosts(self):
        opener = Mock()
        response = Mock()
        opener.open.return_value = response
        with patch.object(server.socket, 'getaddrinfo', return_value=[(2, 1, 6, '', ('93.184.216.34', 443))]), patch.object(server, 'build_opener', return_value=opener):
            server.validate_delivery_link('https://materials.test/file')
            self.assertEqual(opener.open.call_args.kwargs['timeout'], 10)
            response.close.assert_called_once()
        with patch.object(server.socket, 'getaddrinfo', return_value=[(2, 1, 6, '', ('127.0.0.1', 443))]), patch.object(server, 'build_opener', return_value=opener):
            with self.assertRaises(ValueError):
                server.validate_delivery_link('https://private.test/file')


class SMTPReliabilityTest(unittest.TestCase):
    def test_password_reset_uses_common_client_without_logging_token(self):
        with patch.object(server, 'send_email_message') as send, patch('builtins.print') as log:
            server.send_password_reset_email('buyer@example.test', 'https://example.test/reset?token=private')
            self.assertIn('token=private', send.call_args.args[0].get_content())
            send.assert_called_once()
            log.assert_not_called()

    def test_ssl_and_starttls_timeouts(self):
        for use_ssl in (True, False):
            client = Mock()
            client.send_message.return_value = {}
            with patch.multiple(server, SMTP_HOST='smtp.test', MAIL_FROM='sender@test', SMTP_USE_SSL=use_ssl, SMTP_USER='user'), patch.object(server.smtplib, 'SMTP_SSL', return_value=client) as ssl_factory, patch.object(server.smtplib, 'SMTP', return_value=client) as factory:
                server.send_email_message(EmailMessage())
                self.assertEqual((ssl_factory if use_ssl else factory).call_args.kwargs['timeout'], 10)
                self.assertEqual(client.starttls.call_count, 0 if use_ssl else 1)
                client.send_message.assert_called_once()

    def test_connect_failure_safe_send_disconnect_ambiguous_and_quit_failure_accepted(self):
        with patch.multiple(server, SMTP_HOST='smtp.test', MAIL_FROM='sender@test', SMTP_USE_SSL=True):
            with patch.object(server.smtplib, 'SMTP_SSL', side_effect=TimeoutError()):
                with self.assertRaises(server.MailDeliveryError) as result:
                    server.send_email_message(EmailMessage())
                self.assertFalse(result.exception.uncertain)
            client = Mock()
            client.send_message.side_effect = server.smtplib.SMTPServerDisconnected()
            with patch.object(server.smtplib, 'SMTP_SSL', return_value=client):
                with self.assertRaises(server.MailDeliveryError) as result:
                    server.send_email_message(EmailMessage())
                self.assertTrue(result.exception.uncertain)
            client.send_message.side_effect = None
            client.send_message.return_value = {}
            client.quit.side_effect = TimeoutError()
            with patch.object(server.smtplib, 'SMTP_SSL', return_value=client):
                server.send_email_message(EmailMessage())

    def test_authentication_and_tls_failure_are_controlled(self):
        for stage, error in [('login', server.smtplib.SMTPAuthenticationError(535, b'secret-response')), ('starttls', server.ssl.SSLError('secret-response'))]:
            client = Mock()
            getattr(client, stage).side_effect = error
            with patch.multiple(server, SMTP_HOST='smtp.test', MAIL_FROM='sender@test', SMTP_USE_SSL=False, SMTP_USER='user'), patch.object(server.smtplib, 'SMTP', return_value=client), self.assertLogs(level='ERROR') as logs:
                with self.assertRaises(server.MailDeliveryError) as result:
                    server.send_email_message(EmailMessage())
                self.assertFalse(result.exception.uncertain)
                self.assertNotIn('secret-response', ' '.join(logs.output))
