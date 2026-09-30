import re
import unittest

import server


class MorphemicsGamesTest(unittest.TestCase):
    def test_new_games_and_protected_routes_are_wired(self) -> None:
        for slug in ("word-architecture", "palace-restoration"):
            self.assertTrue((server.HTML_GAMES[slug] / server.game_entry_file(slug, "index.html")).is_file())
            token = server.FULL_GAME_ROUTE_TOKENS[slug]
            self.assertRegex(token, r"^\d{12,}$")
            self.assertEqual(server.PROTECTED_FULL_GAME_ROUTES[f"Full-{token}-{slug}"], slug)

    def test_demo_limit_is_injected_only_into_demo_copy(self) -> None:
        source = b"<html><body><button>Play</button></body></html>"
        demo = server.inject_action_limited_demo("word-architecture", source, 100)
        self.assertIn(b"siteDemoLimit", demo)
        self.assertIn(b"const limit=100", demo)
        self.assertNotIn(b"siteDemoLimit", source)

    def test_restoration_email_contains_teacher_instructions(self) -> None:
        note = server.product_email_note(server.SHOP_PRODUCTS["palace-restoration"])
        self.assertIn("АРХИТЕКТОР-2026", note)
        self.assertIn("Добавьте одно слово вручную", note)
        self.assertIn("Записать словарь в этот HTML", note)
        self.assertIn("Онлайн-версия работает без редактирования", note)

    def test_restoration_demo_offers_offline_version_but_paid_copy_does_not(self) -> None:
        source = b"<html><body><button data-duel-teacher-open>Teacher</button></body></html>"
        demo = server.inject_palace_online_read_only(source, show_purchase_notice=True)
        paid = server.inject_palace_online_read_only(source, show_purchase_notice=False)

        self.assertIn("Редактирование словаря в онлайн-версии отключено".encode("utf-8"), demo)
        self.assertIn("Купить офлайн-версию".encode("utf-8"), demo)
        self.assertIn(b"/shop/palace-restoration", demo)
        self.assertNotIn(b"/Full-82057434086961-palace-restoration/offline.html", demo)
        self.assertNotIn("Скачать офлайн-версию".encode("utf-8"), demo)

        self.assertNotIn(b"site-palace-offline-note", paid)
        self.assertNotIn("Купить офлайн-версию".encode("utf-8"), paid)
        self.assertNotIn(b"/shop/palace-restoration", paid)
        self.assertIn(b"data-duel-teacher-open", paid)
        self.assertIn(b"duelWriteTeacherGame", paid)

        product = server.SHOP_PRODUCTS["palace-restoration"]
        self.assertTrue(product["default_url"].endswith("/offline.html"))
        self.assertTrue(product["online_url"].endswith("/index.html"))

        original = (server.HTML_GAMES["palace-restoration"] / server.game_entry_file("palace-restoration", "index.html")).read_text(encoding="utf-8")
        self.assertIn("duelTeacherCode", original)
        self.assertIn("duelWriteTeacherGame", original)

    def test_architecture_email_contains_restoration_full_link(self) -> None:
        note = server.product_email_note(server.SHOP_PRODUCTS["word-architecture"])
        self.assertIn("Реставрация дворца", note)
        self.assertIn("/Full-82057434086961-palace-restoration/index.html", note)

    def test_legal_documents_use_public_contact_and_no_service_headers(self) -> None:
        forbidden = ("Страница /", "Заголовок:", "Текст:", "[email]")
        for filename in server.PUBLIC_DOC_FILES.values():
            text = (server.DOCS_DIR / filename).read_text(encoding="utf-8")
            self.assertFalse(any(marker in text for marker in forbidden), filename)
        for document in server.document_seed_data():
            self.assertIn("anastasia@dimitrieva-av.ru", document["content"])
            self.assertNotRegex(document["content"], re.compile(r"anastasia041191|anastasiasypko"))


if __name__ == "__main__":
    unittest.main()
