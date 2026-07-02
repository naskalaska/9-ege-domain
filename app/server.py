from __future__ import annotations

import hashlib
import hmac
import base64
import csv
import io
import json
import mimetypes
import os
import random
import re
import secrets
import smtplib
import sqlite3
import sys
import ege13_module
import ege10_module
import ege11_module
import ege12_module
import ege14_module
import ege15_module
import ege_orthography_module
import ege5_module
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from email.message import EmailMessage
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import parse_qs, unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "app" / "static"
HTML_DIR = ROOT / "app" / "HTML"
DOCS_DIR = ROOT / "app" / "docs"
DATA_DIR = ROOT / "data"
IMAGES_DIR = ROOT / "images"
WORDS_PATH = ROOT / "ege9_final_grouped_by_orthogram_v4.json"
DB_PATH = DATA_DIR / "ege_app.db"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8088
REPEAT_ON_ERROR = 3
APP_ENV = os.environ.get("APP_ENV", "development").strip().lower()
APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:8088").rstrip("/")
ADMIN_USERNAME = os.environ.get("ADMIN_LOGIN", "admin").strip() or "admin"
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
DEFAULT_DEV_ADMIN_PASSWORD = "admin2026"
PASSWORD_HASH_ITERATIONS = int(os.environ.get("PASSWORD_HASH_ITERATIONS", "260000"))
SMTP_HOST = os.environ.get("SMTP_HOST", "").strip()
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465") or "465")
SMTP_USER = os.environ.get("SMTP_USER", "").strip()
SMTP_PASSWORD_RAW = os.environ.get("SMTP_PASSWORD", "")
SMTP_PASSWORD = "".join(SMTP_PASSWORD_RAW.split()) if any(char.isspace() for char in SMTP_PASSWORD_RAW) else SMTP_PASSWORD_RAW
MAIL_FROM = os.environ.get("MAIL_FROM", SMTP_USER).strip()
SMTP_USE_SSL = os.environ.get("SMTP_USE_SSL", "true").strip().lower() in {"1", "true", "yes", "on"}
CURRENT_PRIVACY_POLICY_VERSION = os.environ.get("PRIVACY_POLICY_VERSION", "2026-06-02").strip()
CURRENT_CONSENT_VERSION = os.environ.get("CONSENT_VERSION", "2026-06-02").strip()
CURRENT_TERMS_VERSION = os.environ.get("TERMS_VERSION", "2026-06-02").strip()
CONSENT_TYPE_PERSONAL_DATA = "personal_data_processing"
FALLBACK_TEACHER_CODE = "T-DDC378"
FALLBACK_TEACHER_EMAIL = "service-teacher@platform.local"
SHOP_PRODUCTS = {
    "fruit-garden-ik-ek": {
        "id": "berry_season",
        "title": "HTML-игра «Фруктовый сад: суффиксы ИК-ЕК»",
        "short_title": "Ягодный сезон",
        "amount": "300.00",
        "currency": "RUB",
        "cover_url": "/assets/shop/kard_fruktovyisad.png",
        "url_env": "BERRY_SEASON_PRODUCT_URL",
        "default_url": f"{APP_BASE_URL}/full-games/berry-season-ik-ek/index.html",
        "kind": "product",
    },
    "dandelion-suffixes": {
        "id": "dandelion_suffixes",
        "title": "HTML-игра «Одуванчик: суффиксы существительных»",
        "short_title": "Одуванчик",
        "amount": "300.00",
        "currency": "RUB",
        "cover_url": "/assets/shop/Kard_oduvanchik.png",
        "url_env": "DANDELION_SUFFIXES_PRODUCT_URL",
        "default_url": "https://disk.yandex.ru/d/IHgUFHcgkK8fAw",
        "kind": "product",
    },
    "mouse-space-game": {
        "id": "mouse_space_game",
        "title": "HTML-игра «Мышонок в космосе: суффиксы прилагательных»",
        "short_title": "Мышонок в космосе",
        "amount": "300.00",
        "currency": "RUB",
        "cover_url": "/assets/shop/cover_mouse_space.png",
        "url_env": "MOUSE_SPACE_PRODUCT_URL",
        "default_url": f"{APP_BASE_URL}/full-games/mouse-space/index.html",
        "kind": "product",
    },
    "homogeneous-members-magic": {
        "id": "focus_homogeneous",
        "title": "HTML-игра «Фокус: однородные члены предложения»",
        "short_title": "Фокус: однородные члены предложения",
        "amount": "500.00",
        "currency": "RUB",
        "cover_url": "/assets/shop/Kard_focus.png",
        "url_env": "HOMOGENEOUS_MEMBERS_MAGIC_PRODUCT_URL",
        "default_url": "https://disk.yandex.ru/d/o4evyJ1A1Flv4Q",
        "kind": "product",
    },
    "paronyms-game": {
        "id": "paronyms_game",
        "title": "HTML-игра «Паронимы: ЕГЭ. Задание 5»",
        "short_title": "Паронимы",
        "amount": "800.00",
        "currency": "RUB",
        "cover_url": "/assets/shop/Kard_paronyms.png",
        "url_env": "PARONYMS_GAME_PRODUCT_URL",
        "default_url": "",
        "kind": "product",
    },
    "verb-conjugation-quest": {
        "id": "verb_conjugation_quest",
        "title": "HTML-игра «Спряжение глагола»",
        "short_title": "Спряжение глагола",
        "amount": "300.00",
        "currency": "RUB",
        "cover_url": "/assets/shop/cover_verb_conjugation.png",
        "url_env": "VERB_CONJUGATION_QUEST_PRODUCT_URL",
        "default_url": f"{APP_BASE_URL}/full-games/verb-conjugation-quest/index.html",
        "kind": "product",
    },
    "truth-action-oge": {
        "id": "truth_action_oge",
        "title": "HTML-игра «Правда, действие, ОГЭ»",
        "short_title": "Правда, действие, ОГЭ",
        "amount": "500.00",
        "currency": "RUB",
        "cover_url": "/assets/shop/cover_truth_action_oge.png",
        "url_env": "TRUTH_ACTION_OGE_PRODUCT_URL",
        "default_url": f"{APP_BASE_URL}/full-games/truth-action-oge/index.html",
        "kind": "product",
    },
    "grammar-zoo": {
        "id": "grammar_zoo",
        "title": "HTML-игра «Зоопарк: грамматические основы»",
        "short_title": "Зоопарк: грамматические основы",
        "amount": "500.00",
        "currency": "RUB",
        "cover_url": "/assets/shop/cover_grammar_zoo.png",
        "url_env": "GRAMMAR_ZOO_PRODUCT_URL",
        "default_url": f"{APP_BASE_URL}/full-games/grammar-zoo/grammar_zoo_engine.html",
        "kind": "product",
    },
    "support-100": {
        "id": "support_100",
        "title": "Поддержка проекта 100 ₽",
        "short_title": "Поддержка проекта",
        "amount": "100.00",
        "currency": "RUB",
        "cover_url": "",
        "url_env": "SUPPORT_100_PRODUCT_URL",
        "default_url": "https://disk.yandex.ru/d/M3avG3To68fHMw",
        "kind": "donation",
    },
    "support-300": {
        "id": "support_300",
        "title": "Поддержка проекта 300 ₽",
        "short_title": "Поддержка проекта",
        "amount": "300.00",
        "currency": "RUB",
        "cover_url": "",
        "url_env": "SUPPORT_300_PRODUCT_URL",
        "default_url": "https://disk.yandex.ru/d/VfpRyCwgn2vkFA",
        "kind": "donation",
    },
    "support-500": {
        "id": "support_500",
        "title": "Поддержка проекта 500 ₽",
        "short_title": "Поддержка проекта",
        "amount": "500.00",
        "currency": "RUB",
        "cover_url": "",
        "url_env": "SUPPORT_500_PRODUCT_URL",
        "default_url": "https://disk.yandex.ru/d/F7r4stcTO4saIw",
        "kind": "donation",
    },
    "support-1000": {
        "id": "support_1000",
        "title": "Поддержка проекта 1000 ₽",
        "short_title": "Поддержка проекта",
        "amount": "1000.00",
        "currency": "RUB",
        "cover_url": "",
        "url_env": "SUPPORT_1000_PRODUCT_URL",
        "default_url": "https://disk.yandex.ru/d/z_guLJ0-kWCIJg",
        "kind": "donation",
    },
}
PRODUCT_BERRY_SEASON = SHOP_PRODUCTS["fruit-garden-ik-ek"]

SESSIONS: dict[str, dict[str, Any]] = {}
PRACTICE_SESSIONS: dict[str, dict[str, Any]] = {}
ACTIVE_VISITORS: dict[str, dict[str, Any]] = {}
ACTIVE_VISITOR_WINDOW_SEC = 300
REGISTRATION_ATTEMPTS: dict[str, list[datetime]] = {}
REGISTRATION_LIMIT_WINDOW_SEC = 600
REGISTRATION_LIMIT_PER_IP = 8

_ege10_scope_id_for = ege10_module.scope_id_for
_ege11_scope_id_for = ege11_module.scope_id_for
_ege12_scope_id_for = ege12_module.scope_id_for
_ege13_scope_id_for = ege13_module.scope_id_for
_ege14_scope_id_for = ege14_module.scope_id_for
_ege15_scope_id_for = ege15_module.scope_id_for
_ege5_scope_id_for = ege5_module.scope_id_for


def ege10_scope_id_for(mode: str, rule_id: str | None = None, rule_ids: list[str] | None = None) -> str:
    return f"ege10:{_ege10_scope_id_for(mode, rule_id, rule_ids)}"


def ege11_scope_id_for(mode: str, rule_id: str | None = None, rule_ids: list[str] | None = None) -> str:
    return f"ege11:{_ege11_scope_id_for(mode, rule_id, rule_ids)}"


def ege12_scope_id_for(mode: str, rule_id: str | None = None, rule_ids: list[str] | None = None) -> str:
    return f"ege12:{_ege12_scope_id_for(mode, rule_id, rule_ids)}"


def ege13_scope_id_for(mode: str, rule_id: str | None = None, rule_ids: list[str] | None = None) -> str:
    return f"ege13:{_ege13_scope_id_for(mode, rule_id, rule_ids)}"


def ege14_scope_id_for(mode: str, rule_id: str | None = None, rule_ids: list[str] | None = None) -> str:
    return f"ege14:{_ege14_scope_id_for(mode, rule_id, rule_ids)}"


def ege15_scope_id_for(mode: str, rule_id: str | None = None, rule_ids: list[str] | None = None) -> str:
    return f"ege15:{_ege15_scope_id_for(mode, rule_id, rule_ids)}"


def ege5_scope_id_for(mode: str, rule_id: str | None = None, rule_ids: list[str] | None = None) -> str:
    return _ege5_scope_id_for(mode, rule_id, rule_ids)


ege10_module.scope_id_for = ege10_scope_id_for
ege11_module.scope_id_for = ege11_scope_id_for
ege12_module.scope_id_for = ege12_scope_id_for
ege13_module.scope_id_for = ege13_scope_id_for
ege14_module.scope_id_for = ege14_scope_id_for
ege15_module.scope_id_for = ege15_scope_id_for
ege5_module.scope_id_for = ege5_scope_id_for

ACTIVITIES = [
    {
        "slug": "ege5",
        "title": "ЕГЭ. Задание 5: паронимы",
        "description": "Паронимы: выбор слова, формат ЕГЭ и верно/неверно.",
        "button": "Открыть тренажёр",
        "kind": "module",
        "group": "орфоэпия, грамматика, речь",
    },
    {
        "slug": "ege9",
        "title": "ЕГЭ. Задание 9",
        "description": "Орфография: корни, гласные, строки с общей буквой.",
        "button": "Открыть тренажёр",
        "kind": "module",
        "group": "Орфография",
    },
    {
        "slug": "ege10",
        "title": "ЕГЭ. Задание 10",
        "description": "Приставки, Ь/Ъ, И/Ы и другие орфограммы задания 10.",
        "button": "Открыть тренажёр",
        "kind": "module",
        "group": "Орфография",
    },
    {
        "slug": "ege11",
        "title": "ЕГЭ. Задание 11",
        "description": "Правописание суффиксов слов разных частей речи.",
        "button": "Открыть тренажёр",
        "kind": "module",
        "group": "Орфография",
    },
    {
        "slug": "ege12",
        "title": "ЕГЭ. Задание 12",
        "description": "Личные окончания глаголов и суффиксы причастий.",
        "button": "Открыть тренажёр",
        "kind": "module",
        "group": "Орфография",
    },
    {
        "slug": "ege13",
        "title": "ЕГЭ. Задание 13",
        "description": "Правописание НЕ с разными частями речи.",
        "button": "Открыть тренажёр",
        "kind": "module",
        "group": "Орфография",
    },
    {
        "slug": "ege14",
        "title": "ЕГЭ. Задание 14",
        "description": "Слитное, раздельное и дефисное написание слов разных частей речи.",
        "button": "Открыть тренажёр",
        "kind": "module",
        "group": "Орфография",
    },
    {
        "slug": "ege15",
        "title": "ЕГЭ. Задание 15",
        "description": "Правописание Н и НН в словах разных частей речи.",
        "button": "Открыть тренажёр",
        "kind": "module",
        "group": "Орфография",
    },
    {
        "slug": "orthography-ege",
        "title": "Орфография. Режимы ЕГЭ",
        "description": "Сборная тренировка по заданиям 9–15: выберите типы заданий и количество.",
        "button": "Собрать тренировку",
        "kind": "module",
        "group": "Орфография",
    },
    {
        "slug": "html-games",
        "title": "Игры",
        "description": "HTML-игры по русскому языку: орфография, пунктуация и культура речи.",
        "button": "Выбрать игру",
        "kind": "mini",
        "group": "Игры",
    },
]

def first_existing_path(*paths: Path) -> Path:
    return next((path for path in paths if path.exists()), paths[0])


HTML_GAMES = {
    "suffixes-nouns": first_existing_path(HTML_DIR / "suffixes-nouns", HTML_DIR / "Лето. Суффиксы"),
    "homogeneous-members-magic": first_existing_path(HTML_DIR / "homogeneous-members-magic", HTML_DIR / "Фокусы"),
    "berry-season-ik-ek": first_existing_path(HTML_DIR / "berry-season-ik-ek", HTML_DIR / "Ягодный сезон ИК-ЕК"),
    "paronyms": first_existing_path(HTML_DIR / "paronyms", HTML_DIR / "Паронимы"),
    "mouse-space": HTML_DIR / "Мышонок в космосе",
    "verb-conjugation-quest": HTML_DIR / "спряжение квест",
    "truth-action-oge": HTML_DIR / "Игра-знакомство",
    "grammar-zoo": HTML_DIR / "Зоопарк - грамматические основы",
}

PUBLIC_GAMES = {
    "fluffs": first_existing_path(HTML_DIR / "fluffs", HTML_DIR / "Пушинки"),
    "suffixes-nouns": first_existing_path(HTML_DIR / "suffixes-nouns", HTML_DIR / "Лето. Суффиксы"),
    "homogeneous-members-magic": first_existing_path(HTML_DIR / "homogeneous-members-magic", HTML_DIR / "Фокусы"),
    "berry-season": first_existing_path(HTML_DIR / "berry-season-ik-ek", HTML_DIR / "Ягодный сезон ИК-ЕК"),
    "berry-season-ik-ek": first_existing_path(HTML_DIR / "berry-season-ik-ek", HTML_DIR / "Ягодный сезон ИК-ЕК"),
    "paronyms": first_existing_path(HTML_DIR / "paronyms", HTML_DIR / "Паронимы"),
    "mouse-space": HTML_DIR / "Мышонок в космосе",
    "verb-conjugation-quest": HTML_DIR / "спряжение квест",
    "truth-action-oge": HTML_DIR / "Игра-знакомство",
    "grammar-zoo": HTML_DIR / "Зоопарк - грамматические основы",
}

GAME_SET_MAX_ITEMS = 200
GAME_SET_MAX_STRING = 600
GAME_SET_MAX_PAYLOAD_BYTES = 200_000
GAME_MECHANICS = {"fluffs", "berry-season", "mouse-space"}
PUBLIC_DOC_FILES = {
    "contacts": "contacts.txt",
    "delivery": "delivery.txt",
    "refund": "refund.txt",
    "offer": "offer.txt",
    "support": "support_stub.txt",
}


def configure_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def seconds_since(value: str | None) -> int | None:
    parsed = parse_iso(value)
    if not parsed:
        return None
    return max(0, int((datetime.now(timezone.utc) - parsed).total_seconds()))


def legacy_password_hash(password: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()


def password_hash(password: str, salt: str) -> str:
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_HASH_ITERATIONS,
    ).hex()
    return f"pbkdf2_sha256${PASSWORD_HASH_ITERATIONS}${salt}${digest}"


def verify_password(password: str, salt: str, stored_hash: str) -> bool:
    if stored_hash.startswith("pbkdf2_sha256$"):
        try:
            _, iterations, stored_salt, digest = stored_hash.split("$", 3)
            candidate = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                stored_salt.encode("utf-8"),
                int(iterations),
            ).hex()
            return hmac.compare_digest(candidate, digest)
        except (TypeError, ValueError):
            return False
    return hmac.compare_digest(legacy_password_hash(password, salt), stored_hash)


def needs_password_rehash(stored_hash: str) -> bool:
    if not stored_hash.startswith("pbkdf2_sha256$"):
        return True
    try:
        _, iterations, _, _ = stored_hash.split("$", 3)
    except ValueError:
        return True
    return int(iterations) < PASSWORD_HASH_ITERATIONS


def production_mode() -> bool:
    return APP_ENV in {"prod", "production"}


def mask_email(value: str) -> str:
    if not value:
        return ""
    if "@" not in value:
        return f"{value[:2]}***"
    local, domain = value.split("@", 1)
    if len(local) <= 2:
        masked_local = f"{local[:1]}***"
    else:
        masked_local = f"{local[:2]}***{local[-1:]}"
    return f"{masked_local}@{domain}"


def smtp_debug_info() -> dict[str, Any]:
    return {
        "host_configured": bool(SMTP_HOST),
        "host": SMTP_HOST,
        "port": SMTP_PORT,
        "use_ssl": SMTP_USE_SSL,
        "user_configured": bool(SMTP_USER),
        "user_masked": mask_email(SMTP_USER),
        "mail_from_configured": bool(MAIL_FROM),
        "mail_from_masked": mask_email(MAIL_FROM),
        "mail_from_matches_user": bool(SMTP_USER and MAIL_FROM and SMTP_USER.lower() == MAIL_FROM.lower()),
        "password_configured": bool(SMTP_PASSWORD_RAW),
        "password_raw_length": len(SMTP_PASSWORD_RAW),
        "password_used_length": len(SMTP_PASSWORD),
        "password_had_whitespace": SMTP_PASSWORD_RAW != SMTP_PASSWORD,
    }


def seed_demo_users() -> bool:
    return os.environ.get("SEED_DEMO_USERS", "1" if not production_mode() else "0") == "1"


def ensure_column(con: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row[1] for row in con.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def seed_paid_entities(con: sqlite3.Connection) -> None:
    now = now_iso()
    for slug, product in SHOP_PRODUCTS.items():
        existing = con.execute(
            "SELECT product_id FROM paid_entities WHERE product_id = ? OR slug = ?",
            (product["id"], slug),
        ).fetchone()
        if existing:
            con.execute(
                """
                UPDATE paid_entities
                SET product_id = ?, slug = ?,
                    title = COALESCE(NULLIF(title, ''), ?),
                    type = ?,
                    amount = COALESCE(NULLIF(amount, ''), ?),
                    currency = COALESCE(NULLIF(currency, ''), ?),
                    delivery_url = COALESCE(NULLIF(delivery_url, ''), ?),
                    cover_url = COALESCE(NULLIF(cover_url, ''), ?),
                    url_env = ?, is_active = COALESCE(is_active, 1), updated_at = ?
                WHERE product_id = ?
                """,
                (
                    product["id"],
                    slug,
                    product["title"],
                    product["kind"],
                    product["amount"],
                    product["currency"],
                    product.get("default_url") or "",
                    product.get("cover_url") or "",
                    product["url_env"],
                    now,
                    existing["product_id"],
                ),
            )
            continue
        con.execute(
            """
            INSERT INTO paid_entities (
                product_id, slug, title, type, amount, currency,
                delivery_url, cover_url, url_env, is_active, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                product["id"],
                slug,
                product["title"],
                product["kind"],
                product["amount"],
                product["currency"],
                product.get("default_url") or "",
                product.get("cover_url") or "",
                product["url_env"],
                now,
                now,
            ),
        )


def document_seed_data() -> list[dict[str, str]]:
    return [
        {
            "document_type": "privacy_policy",
            "version": CURRENT_PRIVACY_POLICY_VERSION,
            "title": "Политика обработки персональных данных",
            "content": (
                "Текст будет заменен после юридической вычитки.\n\n"
                "Платформа хранит учетные записи пользователей, роли, учебный прогресс, попытки выполнения заданий "
                "и технические данные, необходимые для работы сервиса. Рабочая SQLite-база должна храниться на сервере "
                "в Docker volume и не должна попадать в GitHub."
            ),
        },
        {
            "document_type": "personal_data_consent",
            "version": CURRENT_CONSENT_VERSION,
            "title": "Согласие на обработку персональных данных",
            "content": (
                "Текст будет заменен после юридической вычитки.\n\n"
                "Пользователь подтверждает, что ознакомился с Политикой обработки персональных данных и дает согласие "
                "на обработку данных, необходимых для регистрации, авторизации, восстановления пароля, ведения учебного "
                "прогресса и работы кабинетов администратора, учителя и ученика."
            ),
        },
        {
            "document_type": "terms",
            "version": CURRENT_TERMS_VERSION,
            "title": "Пользовательское соглашение",
            "content": (
                "Текст будет заменен после юридической вычитки.\n\n"
                "Этот документ описывает правила использования учебной платформы, учетных записей, тренажёров, "
                "HTML-мини-приложений и кабинетов администратора, учителя и ученика."
            ),
        },
    ]


def seed_documents(con: sqlite3.Connection) -> None:
    for document in document_seed_data():
        con.execute(
            """
            INSERT INTO documents
                (id, document_type, version, title, content, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 1, ?, ?)
            ON CONFLICT(document_type, version) DO UPDATE SET
                title = excluded.title,
                content = excluded.content,
                is_active = 1,
                updated_at = excluded.updated_at
            """,
            (
                f"{document['document_type']}:{document['version']}",
                document["document_type"],
                document["version"],
                document["title"],
                document["content"],
                now_iso(),
                now_iso(),
            ),
        )


def ensure_admin_role_supported(con: sqlite3.Connection) -> None:
    table = con.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'users'"
    ).fetchone()
    if not table or "'admin'" in (table[0] or ""):
        return

    con.execute("PRAGMA foreign_keys = OFF")
    con.execute("ALTER TABLE users RENAME TO users_old")
    con.execute(
        """
        CREATE TABLE users (
            user_id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            display_name TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'teacher', 'student')),
            password_salt TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
                teacher_code TEXT,
                teacher_id TEXT,
                password_reset_required INTEGER NOT NULL DEFAULT 0
            )
        """
    )
    con.execute(
        """
        INSERT INTO users
            (user_id, username, display_name, role, password_salt, password_hash,
             created_at, teacher_code, teacher_id)
        SELECT user_id, username, display_name, role, password_salt, password_hash,
               created_at, teacher_code, teacher_id
        FROM users_old
        """
    )
    con.execute("DROP TABLE users_old")
    con.execute("PRAGMA foreign_keys = ON")


def ensure_app_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                display_name TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('admin', 'teacher', 'student')),
                password_salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                teacher_code TEXT,
                teacher_id TEXT
            );

            CREATE TABLE IF NOT EXISTS attempts (
                attempt_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                mode TEXT NOT NULL,
                scope_id TEXT,
                word_id TEXT,
                rule_id TEXT,
                category TEXT,
                rule_name TEXT,
                question_id TEXT NOT NULL,
                prompt TEXT NOT NULL,
                given_answer TEXT,
                correct_answer TEXT NOT NULL,
                is_correct INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                time_spent_sec INTEGER,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS word_progress (
                user_id TEXT NOT NULL,
                scope_id TEXT NOT NULL,
                word_id TEXT NOT NULL,
                cycle_seen INTEGER NOT NULL DEFAULT 0,
                due_reviews INTEGER NOT NULL DEFAULT 0,
                correct_count INTEGER NOT NULL DEFAULT 0,
                error_count INTEGER NOT NULL DEFAULT 0,
                last_seen_at TEXT,
                PRIMARY KEY(user_id, scope_id, word_id),
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                token_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                token_hash TEXT UNIQUE NOT NULL,
                expires_at TEXT NOT NULL,
                used_at TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                document_type TEXT NOT NULL,
                version TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(document_type, version)
            );

            CREATE TABLE IF NOT EXISTS user_consents (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                consent_type TEXT NOT NULL,
                document_version TEXT NOT NULL,
                accepted_at TEXT NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                UNIQUE(user_id, consent_type, document_version)
            );

            CREATE TABLE IF NOT EXISTS game_sets (
                id TEXT PRIMARY KEY,
                public_id TEXT UNIQUE NOT NULL,
                teacher_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                mechanic TEXT NOT NULL,
                source_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(teacher_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS shop_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_uid TEXT UNIQUE,
                product_id TEXT,
                product_title TEXT,
                amount TEXT,
                currency TEXT DEFAULT 'RUB',
                buyer_email TEXT,
                yookassa_payment_id TEXT,
                status TEXT DEFAULT 'pending',
                email_sent INTEGER DEFAULT 0,
                created_at TEXT,
                paid_at TEXT NULL,
                raw_webhook TEXT NULL
            );

            CREATE TABLE IF NOT EXISTS paid_entities (
                product_id TEXT PRIMARY KEY,
                slug TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('product', 'donation')),
                amount TEXT NOT NULL,
                currency TEXT DEFAULT 'RUB',
                delivery_url TEXT,
                cover_url TEXT,
                url_env TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS game_visits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT NOT NULL,
                public_id TEXT,
                path TEXT,
                opened_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_attempts_user_id ON attempts(user_id);
            CREATE INDEX IF NOT EXISTS idx_attempts_mode ON attempts(mode);
            CREATE INDEX IF NOT EXISTS idx_attempts_created_at ON attempts(created_at);
            CREATE INDEX IF NOT EXISTS idx_word_progress_user_scope ON word_progress(user_id, scope_id);
            CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_hash ON password_reset_tokens(token_hash);
            CREATE INDEX IF NOT EXISTS idx_user_consents_user_type ON user_consents(user_id, consent_type);
            CREATE INDEX IF NOT EXISTS idx_documents_type_active ON documents(document_type, is_active);
            CREATE INDEX IF NOT EXISTS idx_game_sets_teacher ON game_sets(teacher_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_shop_orders_uid ON shop_orders(order_uid);
            CREATE INDEX IF NOT EXISTS idx_shop_orders_payment ON shop_orders(yookassa_payment_id);
            CREATE INDEX IF NOT EXISTS idx_game_visits_opened_at ON game_visits(opened_at);
            CREATE INDEX IF NOT EXISTS idx_paid_entities_slug ON paid_entities(slug);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_users_teacher_code
                ON users(teacher_code)
                WHERE teacher_code IS NOT NULL;
            """
        )
        ensure_column(con, "users", "teacher_code", "TEXT")
        ensure_column(con, "users", "teacher_id", "TEXT")
        ensure_column(con, "users", "email", "TEXT")
        ensure_column(con, "users", "password_reset_required", "INTEGER NOT NULL DEFAULT 0")
        ensure_admin_role_supported(con)
        con.execute("UPDATE users SET email = LOWER(username) WHERE email IS NULL AND instr(username, '@') > 1")
        con.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email
                ON users(LOWER(email))
                WHERE email IS NOT NULL AND email <> ''
            """
        )
        ensure_column(con, "attempts", "scope_id", "TEXT")
        ensure_column(con, "attempts", "word_id", "TEXT")
        ensure_column(con, "game_sets", "is_active", "INTEGER NOT NULL DEFAULT 1")
        ensure_column(con, "game_sets", "last_used_at", "TEXT")
        ensure_column(con, "game_sets", "use_count", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(con, "game_sets", "deactivated_at", "TEXT")
        ensure_column(con, "game_sets", "deactivated_by", "TEXT")
        ensure_column(con, "game_sets", "is_deleted", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(con, "game_sets", "deleted_at", "TEXT")
        ensure_column(con, "game_sets", "deleted_by", "TEXT")
        ensure_column(con, "shop_orders", "receipt_sent", "INTEGER NOT NULL DEFAULT 0")
        ensure_column(con, "shop_orders", "receipt_sent_at", "TEXT")
        ensure_column(con, "shop_orders", "receipt_note", "TEXT")
        ensure_column(con, "paid_entities", "cover_url", "TEXT")
        seed_paid_entities(con)
        seed_documents(con)
        ensure_service_admin(con)
        ensure_fallback_teacher(con)
        if seed_demo_users():
            seed_user(con, "teacher", "teacher123", "teacher", "Учитель")
            seed_user(con, "student", "student123", "student", "Ученик")
            con.execute(
                """
                UPDATE users
                SET teacher_code = COALESCE(teacher_code, 'TEACHER-2026'),
                    display_name = 'Учитель'
                WHERE username = 'teacher'
                """
            )
            con.execute(
                """
                UPDATE users
                SET teacher_id = COALESCE(teacher_id, 'user_teacher'),
                    display_name = 'Ученик'
                WHERE username = 'student'
                """
            )


def seed_user(con: sqlite3.Connection, username: str, password: str, role: str, display_name: str) -> None:
    exists = con.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone()
    if exists:
        return
    salt = secrets.token_hex(16)
    con.execute(
        """
        INSERT INTO users (user_id, username, display_name, role, password_salt, password_hash, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (f"user_{username}", username, display_name, role, salt, password_hash(password, salt), now_iso()),
    )


def ensure_service_admin(con: sqlite3.Connection) -> None:
    existing = con.execute("SELECT 1 FROM users WHERE username = ?", (ADMIN_USERNAME,)).fetchone()
    admin_password = ADMIN_PASSWORD
    if not admin_password:
        if existing:
            return
        if production_mode():
            raise RuntimeError("ADMIN_PASSWORD must be set before creating the first admin in production.")
        admin_password = DEFAULT_DEV_ADMIN_PASSWORD
    if production_mode() and admin_password in {"admin", "admin2026", "password", "teacher123", "student123"}:
        raise RuntimeError("ADMIN_PASSWORD is too obvious for production.")

    salt = secrets.token_hex(16)
    hashed = password_hash(admin_password, salt)
    if existing:
        con.execute(
            """
            UPDATE users
            SET user_id = 'user_admin',
                display_name = 'Администратор',
                role = 'admin',
                password_salt = ?,
                password_hash = ?,
                teacher_code = NULL,
                teacher_id = NULL
            WHERE username = ?
            """,
            (salt, hashed, ADMIN_USERNAME),
        )
        return
    con.execute(
        """
        INSERT INTO users
            (user_id, username, display_name, role, password_salt, password_hash, created_at)
        VALUES ('user_admin', ?, 'Администратор', 'admin', ?, ?, ?)
        """,
        (ADMIN_USERNAME, salt, hashed, now_iso()),
    )


def make_teacher_code() -> str:
    return f"T-{secrets.token_hex(3).upper()}"


def make_unique_teacher_code(con: sqlite3.Connection) -> str:
    for _ in range(20):
        code = make_teacher_code()
        exists = con.execute("SELECT 1 FROM users WHERE teacher_code = ?", (code,)).fetchone()
        if not exists:
            return code
    raise RuntimeError("Could not generate a unique teacher code.")


def normalize_email(value: Any) -> str:
    return str(value or "").strip().lower()


def validate_email(email: str) -> None:
    if not email:
        raise ValueError("Укажите email.")
    if len(email) > 254:
        raise ValueError("Email слишком длинный.")
    if not re.fullmatch(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9-]+(?:\.[a-z0-9-]+)+", email):
        raise ValueError("Укажите корректный email.")
    if email.count("@") != 1:
        raise ValueError("Укажите корректный email.")
    local, domain = email.rsplit("@", 1)
    if not local or len(local) > 64 or not domain or "." not in domain.strip("."):
        raise ValueError("Укажите корректный email.")
    if local.startswith(".") or local.endswith(".") or ".." in local:
        raise ValueError("Укажите корректный email.")
    if any(part.startswith("-") or part.endswith("-") for part in domain.split(".")):
        raise ValueError("Укажите корректный email.")


def validate_registration_email(email: str) -> None:
    validate_email(email)
    domain = email.rsplit("@", 1)[1].strip(".")
    if not domain.endswith(".ru"):
        raise ValueError("Регистрация доступна только с email в доменной зоне .ru.")
    local = email.rsplit("@", 1)[0]
    if domain == "test.ru" or domain.endswith(".test.ru"):
        raise ValueError("Для регистрации укажите настоящий email, тестовые адреса не принимаются.")
    if re.fullmatch(r"(bot|test|xss|audit)[._-]?\d*", local) or local.startswith(("bot", "xss_test", "audit_test_ege")):
        raise ValueError("Для регистрации укажите настоящий email, тестовые адреса не принимаются.")


def normalize_display_name(value: Any, fallback: str) -> str:
    display_name = re.sub(r"\s+", " ", str(value or fallback).strip())
    if not display_name:
        display_name = fallback
    if len(display_name) < 2:
        raise ValueError("Имя должно быть не короче 2 символов.")
    if len(display_name) > 80:
        raise ValueError("Имя должно быть не длиннее 80 символов.")
    if any(char in display_name for char in "<>\"'`{}[];"):
        raise ValueError("Имя содержит недопустимые символы. Можно использовать буквы, пробел, дефис, точку и подчёркивание.")
    if not re.fullmatch(r"[A-Za-zА-Яа-яЁё0-9 ._-]+", display_name):
        raise ValueError("Имя содержит недопустимые символы. Можно использовать буквы, пробел, дефис, точку и подчёркивание.")
    return display_name


def log_suspicious_registration(reason: str, email: str, ip_address: str, user_agent: str) -> None:
    print(
        f"[security] suspicious registration: reason={reason}; email={email[:120]}; ip={ip_address[:80]}; ua={user_agent[:160]}",
        file=sys.stderr,
    )


def check_registration_honeypot(payload: dict[str, Any], email: str, ip_address: str, user_agent: str) -> None:
    for field in ("website", "homepage", "company_url"):
        if str(payload.get(field) or "").strip():
            log_suspicious_registration(f"honeypot:{field}", email, ip_address, user_agent)
            raise ValueError("Регистрацию не удалось завершить. Проверьте данные и попробуйте ещё раз.")


def check_registration_rate_limit(ip_address: str, email: str, user_agent: str) -> None:
    key = (ip_address or "unknown").strip()[:80]
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=REGISTRATION_LIMIT_WINDOW_SEC)
    attempts = [item for item in REGISTRATION_ATTEMPTS.get(key, []) if item >= cutoff]
    if len(attempts) >= REGISTRATION_LIMIT_PER_IP:
        log_suspicious_registration("rate_limit", email, key, user_agent)
        REGISTRATION_ATTEMPTS[key] = attempts
        raise ValueError("Слишком много регистраций с этого адреса. Попробуйте позже.")
    attempts.append(now)
    REGISTRATION_ATTEMPTS[key] = attempts


def ensure_fallback_teacher(con: sqlite3.Connection) -> None:
    row = con.execute(
        "SELECT * FROM users WHERE role = 'teacher' AND UPPER(teacher_code) = ?",
        (FALLBACK_TEACHER_CODE,),
    ).fetchone()
    if row:
        if "email" in row.keys() and not row["email"]:
            con.execute(
                "UPDATE users SET email = ? WHERE user_id = ?",
                (FALLBACK_TEACHER_EMAIL, row["user_id"]),
            )
        return

    salt = secrets.token_hex(16)
    con.execute(
        """
        INSERT INTO users
            (user_id, username, email, display_name, role, password_salt, password_hash,
             created_at, teacher_code, password_reset_required)
        VALUES (?, ?, ?, ?, 'teacher', ?, ?, ?, ?, 1)
        """,
        (
            "user_service_teacher",
            FALLBACK_TEACHER_EMAIL,
            FALLBACK_TEACHER_EMAIL,
            "Служебный учитель",
            salt,
            password_hash(secrets.token_urlsafe(32), salt),
            now_iso(),
            FALLBACK_TEACHER_CODE,
        ),
    )


def register_user(payload: dict[str, Any], ip_address: str = "", user_agent: str = "") -> dict[str, Any]:
    email = normalize_email(payload.get("email"))
    username = email
    password = str(payload.get("password") or "")
    check_registration_honeypot(payload, email, ip_address, user_agent)
    check_registration_rate_limit(ip_address, email, user_agent)
    display_name = normalize_display_name(payload.get("display_name"), username.rsplit("@", 1)[0] or username)
    role = str(payload.get("role") or "student").strip()
    teacher_code = str(payload.get("teacher_code") or "").strip().upper()
    consent_accepted = bool(payload.get("consent_accepted"))

    if role not in {"teacher", "student"}:
        raise ValueError("Неизвестная роль.")
    if not consent_accepted:
        raise ValueError("Для регистрации необходимо принять Политику обработки персональных данных и дать согласие на обработку персональных данных.")
    validate_registration_email(email)
    if len(password) < 6:
        raise ValueError("Пароль должен быть не короче 6 символов.")
    if role == "student" and not teacher_code:
        teacher_code = FALLBACK_TEACHER_CODE

    should_send_email = False
    buyer_email = ""
    with db() as con:
        ensure_fallback_teacher(con)
        teacher_id = None
        own_teacher_code = None
        if role == "student":
            teacher = con.execute(
                "SELECT user_id FROM users WHERE role = 'teacher' AND UPPER(teacher_code) = ?",
                (teacher_code,),
            ).fetchone()
            if not teacher:
                raise ValueError("Код учителя не найден.")
            teacher_id = teacher["user_id"]
        else:
            own_teacher_code = make_unique_teacher_code(con)

        existing = con.execute(
            "SELECT * FROM users WHERE LOWER(COALESCE(email, '')) = ? OR LOWER(username) = ?",
            (email, username),
        ).fetchone()
        if existing:
            if not int(existing["password_reset_required"] or 0):
                raise ValueError("Пользователь с таким email уже зарегистрирован")
            if existing["role"] != role:
                raise ValueError("Для восстановления выберите прежнюю роль.")
            if role == "student" and existing["teacher_id"] != teacher_id:
                raise ValueError("Код учителя не совпадает с текущим аккаунтом.")
            salt = secrets.token_hex(16)
            con.execute(
                """
                UPDATE users
                SET display_name = COALESCE(NULLIF(?, ''), display_name),
                    username = ?,
                    email = ?,
                    password_salt = ?,
                    password_hash = ?,
                    password_reset_required = 0
                WHERE user_id = ?
                """,
                (display_name, username, email, salt, password_hash(password, salt), existing["user_id"]),
            )
            row = con.execute("SELECT * FROM users WHERE user_id = ?", (existing["user_id"],)).fetchone()
            insert_user_consent(con, row["user_id"], ip_address, user_agent)
            user = public_user(row)
            user["has_required_consents"] = True
            return user

        salt = secrets.token_hex(16)
        user_id = f"user_{secrets.token_hex(8)}"
        con.execute(
            """
            INSERT INTO users
                (user_id, username, email, display_name, role, password_salt, password_hash,
                 created_at, teacher_code, teacher_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                username,
                email,
                display_name,
                role,
                salt,
                password_hash(password, salt),
                now_iso(),
                own_teacher_code,
                teacher_id,
            ),
        )
        row = con.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        insert_user_consent(con, user_id, ip_address, user_agent)
    user = public_user(row)
    user["has_required_consents"] = True
    return user


def load_words() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    data = json.loads(WORDS_PATH.read_text(encoding="utf-8"))
    words: list[dict[str, Any]] = []
    rules: list[dict[str, Any]] = []
    for category, grouped_rules in data.get("categories", {}).items():
        for rule_name, items in grouped_rules.items():
            rule_id = make_rule_id(category, rule_name)
            rule_words = []
            for item in items:
                if not item.get("variant") or not item.get("correct_letter"):
                    continue
                word = {
                    "id": str(item.get("id") or f"{rule_id}_{len(words)}"),
                    "category": category,
                    "rule_name": rule_name,
                    "rule_id": rule_id,
                    "variant": item.get("variant"),
                    "correct_letter": str(item.get("correct_letter") or item.get("answer")).strip().lower(),
                    "correct_spelling": item.get("correct_spelling") or "",
                    "explanation": item.get("explanation") or "",
                    "dependency": item.get("dependency") or "",
                    "address": item.get("first_address") or "",
                }
                words.append(word)
                rule_words.append(word)
            rules.append(
                {
                    "rule_id": rule_id,
                    "category": category,
                    "rule_name": rule_name,
                    "count": len(rule_words),
                }
            )
    return words, rules


def make_rule_id(category: str, rule_name: str) -> str:
    return hashlib.sha1(f"{category}::{rule_name}".encode("utf-8")).hexdigest()[:16]


WORDS, RULES = load_words()
WORD_BY_ID = {word["id"]: word for word in WORDS}
WORDS_BY_RULE: dict[str, list[dict[str, Any]]] = {}
for word in WORDS:
    WORDS_BY_RULE.setdefault(word["rule_id"], []).append(word)
RULE_BY_ID = {rule["rule_id"]: rule for rule in RULES}


def category_progress_for_user(
    user_id: str | None,
    rules: list[dict[str, Any]],
    words_by_rule: dict[str, list[dict[str, Any]]],
    scope_func: Any = None,
) -> dict[str, dict[str, int]]:
    scope_func = scope_func or scope_id_for
    progress: dict[str, dict[str, int]] = {}
    for rule in rules:
        category = rule["category"]
        progress.setdefault(category, {"total": 0, "solved": 0})
        progress[category]["total"] += int(rule.get("count") or len(words_by_rule.get(rule["rule_id"], [])))
    if not user_id:
        return progress

    with db() as con:
        for category in progress:
            word_ids = [
                word["id"]
                for rule in rules
                if rule["category"] == category
                for word in words_by_rule.get(rule["rule_id"], [])
            ]
            if not word_ids:
                continue
            solved_ids: set[str] = set()
            due_error_ids: set[str] = set()
            for chunk in chunked(word_ids):
                placeholders = ",".join("?" for _ in chunk)
                rows = con.execute(
                    f"""
                    SELECT DISTINCT word_id
                    FROM attempts
                    WHERE user_id = ?
                      AND category = ?
                      AND is_correct = 1
                      AND word_id IN ({placeholders})
                    """,
                    (user_id, category, *chunk),
                ).fetchall()
                solved_ids.update(row["word_id"] for row in rows)
                due_rows = con.execute(
                    f"""
                    SELECT DISTINCT word_id
                    FROM word_progress
                    WHERE user_id = ?
                      AND scope_id = ?
                      AND due_reviews > 0
                      AND word_id IN ({placeholders})
                    """,
                    (user_id, scope_func("errors"), *chunk),
                ).fetchall()
                due_error_ids.update(row["word_id"] for row in due_rows)
            progress[category]["solved"] = len(solved_ids - due_error_ids)
    return progress


def bootstrap_for(
    rules: list[dict[str, Any]],
    word_count: int,
    user_id: str | None = None,
    words_by_rule: dict[str, list[dict[str, Any]]] | None = None,
    scope_func: Any = None,
) -> dict[str, Any]:
    scope_func = scope_func or scope_id_for
    grouped: dict[str, list[dict[str, Any]]] = {}
    for rule in rules:
        grouped.setdefault(rule["category"], []).append(rule)
    words_by_rule = words_by_rule or WORDS_BY_RULE
    return {
        "rules": grouped,
        "word_count": word_count,
        "repeat_on_error": REPEAT_ON_ERROR,
        "activities": ACTIVITIES,
        "category_progress": category_progress_for_user(user_id, rules, words_by_rule, scope_func),
    }


def activity_bootstrap(slug: str, user: dict[str, Any] | None = None) -> dict[str, Any]:
    user_id = user["user_id"] if user else None
    if slug == "ege5":
        return bootstrap_for(ege5_module.RULES, len(ege5_module.ROWS), user_id, ege5_module.GROUPS_BY_RULE, ege5_module.scope_id_for)
    if slug == "ege9":
        return bootstrap_for(RULES, len(WORDS), user_id, WORDS_BY_RULE, scope_id_for)
    if slug == "ege10":
        return bootstrap_for(ege10_module.RULES, len(ege10_module.WORDS), user_id, ege10_module.WORDS_BY_RULE, ege10_module.scope_id_for)
    if slug == "ege11":
        return bootstrap_for(ege11_module.RULES, len(ege11_module.WORDS), user_id, ege11_module.WORDS_BY_RULE, ege11_module.scope_id_for)
    if slug == "ege12":
        return bootstrap_for(ege12_module.RULES, len(ege12_module.WORDS), user_id, ege12_module.WORDS_BY_RULE, ege12_module.scope_id_for)
    if slug == "ege13":
        return bootstrap_for(ege13_module.RULES, len(ege13_module.WORDS), user_id, ege13_module.WORDS_BY_RULE, ege13_module.scope_id_for)
    if slug == "ege14":
        return bootstrap_for(ege14_module.RULES, len(ege14_module.WORDS), user_id, ege14_module.WORDS_BY_RULE, ege14_module.scope_id_for)
    if slug == "ege15":
        return bootstrap_for(ege15_module.RULES, len(ege15_module.WORDS), user_id, ege15_module.WORDS_BY_RULE, ege15_module.scope_id_for)
    if slug == "orthography-ege":
        return {
            "activity": next(item for item in ACTIVITIES if item["slug"] == "orthography-ege"),
            "rules": {},
            "word_count": (
                len(WORDS)
                + len(ege10_module.WORDS)
                + len(ege11_module.WORDS)
                + len(ege12_module.WORDS)
                + len(ege13_module.WORDS)
                + len(ege14_module.WORDS)
                + len(ege15_module.WORDS)
            ),
            "activities": ACTIVITIES,
            "category_progress": {},
        }
    if slug == "html-games":
        return {
            "activity": next(item for item in ACTIVITIES if item["slug"] == "html-games"),
            "activities": ACTIVITIES,
        }
    raise ValueError("Активность не найдена.")


def activity_post(slug: str, action: str, user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    if slug == "ege5":
        if action == "start":
            return ege5_module.start_practice(user, payload)
        if action == "submit":
            return ege5_module.submit_practice(user, payload)
        if action == "check":
            return ege5_module.check_practice_answer(user, payload)
    if slug == "ege9":
        if action == "start":
            return start_practice(user, payload)
        if action == "submit":
            return submit_practice(user, payload)
        if action == "check":
            return check_practice_answer(user, payload)
    if slug == "ege10":
        if action == "start":
            return ege10_module.start_practice(user, payload)
        if action == "submit":
            return ege10_module.submit_practice(user, payload)
        if action == "check":
            return ege10_module.check_practice_answer(user, payload)
    if slug == "ege11":
        if action == "start":
            return ege11_module.start_practice(user, payload)
        if action == "submit":
            return ege11_module.submit_practice(user, payload)
        if action == "check":
            return ege11_module.check_practice_answer(user, payload)
    if slug == "ege12":
        if action == "start":
            return ege12_module.start_practice(user, payload)
        if action == "submit":
            return ege12_module.submit_practice(user, payload)
        if action == "check":
            return ege12_module.check_practice_answer(user, payload)
    if slug == "ege13":
        if action == "start":
            return ege13_module.start_practice(user, payload)
        if action == "submit":
            return ege13_module.submit_practice(user, payload)
        if action == "check":
            return ege13_module.check_practice_answer(user, payload)
    if slug == "ege14":
        if action == "start":
            return ege14_module.start_practice(user, payload)
        if action == "submit":
            return ege14_module.submit_practice(user, payload)
        if action == "check":
            return ege14_module.check_practice_answer(user, payload)
    if slug == "ege15":
        if action == "start":
            return ege15_module.start_practice(user, payload)
        if action == "submit":
            return ege15_module.submit_practice(user, payload)
        if action == "check":
            return ege15_module.check_practice_answer(user, payload)
    if slug == "orthography-ege":
        if action == "start":
            return ege_orthography_module.start_practice(user, payload)
        if action == "submit":
            return ege_orthography_module.submit_practice(user, payload)
        if action == "check":
            return ege_orthography_module.check_practice_answer(user, payload)
    raise ValueError("Действие активности не найдено.")


def db() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def required_consents() -> list[dict[str, str]]:
    return [
        {
            "consent_type": CONSENT_TYPE_PERSONAL_DATA,
            "document_version": CURRENT_CONSENT_VERSION,
            "privacy_policy_version": CURRENT_PRIVACY_POLICY_VERSION,
        }
    ]


def active_document(document_type: str) -> dict[str, Any]:
    with db() as con:
        row = con.execute(
            """
            SELECT document_type, version, title, content, updated_at
            FROM documents
            WHERE document_type = ? AND is_active = 1
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (document_type,),
        ).fetchone()
    if not row:
        raise ValueError("Документ не найден.")
    return dict(row)


def public_text_document(slug: str) -> dict[str, str]:
    filename = PUBLIC_DOC_FILES.get(slug)
    if not filename:
        raise ValueError("Документ не найден.")
    path = (DOCS_DIR / filename).resolve()
    try:
        path.relative_to(DOCS_DIR.resolve())
    except ValueError:
        raise ValueError("Документ не найден.")
    if not path.is_file():
        raise ValueError("Документ не найден.")
    return {
        "slug": slug,
        "filename": filename,
        "content": path.read_text(encoding="utf-8"),
    }


def consent_status(user_id: str) -> dict[str, Any]:
    with db() as con:
        accepted_rows = con.execute(
            """
            SELECT consent_type, document_version, accepted_at
            FROM user_consents
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchall()
    accepted = {(row["consent_type"], row["document_version"]): row for row in accepted_rows}
    required = []
    for item in required_consents():
        key = (item["consent_type"], item["document_version"])
        row = accepted.get(key)
        required.append(
            {
                **item,
                "accepted": row is not None,
                "accepted_at": row["accepted_at"] if row else None,
            }
        )
    return {
        "has_required_consents": all(item["accepted"] for item in required),
        "required": required,
    }


def user_has_required_consents(user_id: str) -> bool:
    return bool(consent_status(user_id)["has_required_consents"])


def insert_user_consent(con: sqlite3.Connection, user_id: str, ip_address: str = "", user_agent: str = "") -> None:
    item = required_consents()[0]
    con.execute(
        """
        INSERT INTO user_consents
            (id, user_id, consent_type, document_version, accepted_at, ip_address, user_agent)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id, consent_type, document_version) DO UPDATE SET
            accepted_at = excluded.accepted_at,
            ip_address = excluded.ip_address,
            user_agent = excluded.user_agent
        """,
        (
            secrets.token_hex(12),
            user_id,
            item["consent_type"],
            item["document_version"],
            now_iso(),
            ip_address,
            user_agent[:500] if user_agent else "",
        ),
    )


def record_user_consent(user_id: str, ip_address: str = "", user_agent: str = "") -> dict[str, Any]:
    with db() as con:
        insert_user_consent(con, user_id, ip_address, user_agent)
    return consent_status(user_id)


def public_user(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    has_consents = user_has_required_consents(row["user_id"])
    email = row["email"] if "email" in row.keys() else None
    return {
        "user_id": row["user_id"],
        "username": row["username"],
        "email": email,
        "display_name": row["display_name"],
        "role": row["role"],
        "teacher_code": row["teacher_code"] if row["role"] == "teacher" else None,
        "teacher_id": row["teacher_id"] if row["role"] == "student" else None,
        "has_required_consents": has_consents,
    }


def require_admin(user: dict[str, Any]) -> None:
    if user["role"] != "admin":
        raise PermissionError("Админ-страница доступна только администратору.")


def parse_json_body(handler: SimpleHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length") or 0)
    if not length:
        return {}
    return json.loads(handler.rfile.read(length).decode("utf-8"))


def scope_id_for(mode: str, rule_id: str | None = None, rule_ids: list[str] | None = None) -> str:
    if mode in {"rule", "word_letter"}:
        if rule_ids:
            digest = hashlib.sha1("|".join(sorted(rule_ids)).encode("utf-8")).hexdigest()[:16]
            return f"{mode}:rules:{digest}"
        return f"rule:{rule_id}"
    if mode == "mix":
        return "mix:all"
    if mode == "errors":
        return "errors:bank"
    return mode


def normalize_letter(value: Any) -> str:
    return str(value or "").strip().lower().replace("ё", "ё")[:1]


def letter_choices(word: dict[str, Any]) -> list[str]:
    correct = normalize_letter(word["correct_letter"])
    marker = f"{word['category']} {word['rule_name']} {word['dependency']} {word.get('root', '')}".lower()
    common_letters = ["а", "о", "е", "и", "ы", "я", "ю", "э", "ё", "у"]

    if "после ц" in marker and correct in {"и", "ы"}:
        priority = ["и", "ы"]
    elif "шип" in marker and correct in {"о", "ё", "е"}:
        priority = ["о", "ё", "е"]
    elif correct in {"а", "о"}:
        priority = ["а", "о"]
    elif correct in {"и", "е"}:
        priority = ["и", "е"]
    elif correct in {"я", "а"}:
        priority = ["я", "а"]
    elif correct in {"ю", "у"}:
        priority = ["ю", "у"]
    else:
        priority = [correct]

    choices: list[str] = []
    for letter in priority:
        letter = normalize_letter(letter)
        if letter and letter not in choices:
            choices.append(letter)

    if len(choices) <= 1:
        for letter in common_letters:
            letter = normalize_letter(letter)
            if letter and letter not in choices:
                choices.append(letter)
            if len(choices) >= 4:
                break

    random.shuffle(choices)
    if correct not in choices:
        choices[0] = correct
        random.shuffle(choices)
    return choices


def make_word_question(word: dict[str, Any]) -> dict[str, Any]:
    return {
        "question_id": secrets.token_hex(8),
        "kind": "word",
        "source_word_id": word["id"],
        "prompt": word["variant"],
        "choices": letter_choices(word),
        "category": word["category"],
        "rule_id": word["rule_id"],
        "rule_name": word["rule_name"],
        "explanation": word["explanation"],
        "correct_spelling": word["correct_spelling"],
        "address": word["address"],
        "_correct_answer": word["correct_letter"],
    }


def chunked(items: list[str], size: int = 700) -> list[list[str]]:
    return [items[index:index + size] for index in range(0, len(items), size)]


def solved_word_ids_for_pool(con: sqlite3.Connection, user_id: str, word_ids: list[str]) -> set[str]:
    solved: set[str] = set()
    for chunk in chunked(word_ids):
        placeholders = ",".join("?" for _ in chunk)
        rows = con.execute(
            f"""
            SELECT DISTINCT word_id
            FROM word_progress
            WHERE user_id = ?
              AND scope_id <> ?
              AND due_reviews = 0
              AND cycle_seen = 1
              AND word_id IN ({placeholders})
            """,
            (user_id, scope_id_for("errors"), *chunk),
        ).fetchall()
        solved.update(row["word_id"] for row in rows)
    return solved


def pick_words_for_scope(user_id: str, scope_id: str, pool: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    if not pool:
        return []

    pool_by_id = {word["id"]: word for word in pool}
    selected: list[dict[str, Any]] = []
    with db() as con:
        if scope_id != scope_id_for("errors"):
            error_rows = con.execute(
                """
                SELECT word_id, due_reviews, last_seen_at
                FROM word_progress
                WHERE user_id = ? AND scope_id = ? AND due_reviews > 0
                ORDER BY due_reviews DESC, last_seen_at ASC
                """,
                (user_id, scope_id_for("errors")),
            ).fetchall()
            for row in error_rows:
                word_id = row["word_id"]
                if word_id in pool_by_id and word_id not in {word["id"] for word in selected}:
                    selected.append(pool_by_id[word_id])
                if len(selected) >= count:
                    return selected

        rows = con.execute(
            """
            SELECT word_id, cycle_seen, due_reviews, last_seen_at
            FROM word_progress
            WHERE user_id = ? AND scope_id = ?
            """,
            (user_id, scope_id),
        ).fetchall()
        progress = {row["word_id"]: row for row in rows if row["word_id"] in pool_by_id}

        due = [
            row
            for row in sorted(progress.values(), key=lambda item: (item["last_seen_at"] or "", item["word_id"]))
            if int(row["due_reviews"]) > 0
        ]
        selected_ids = {word["id"] for word in selected}
        for row in due[:count]:
            if row["word_id"] in selected_ids:
                continue
            selected.append(pool_by_id[row["word_id"]])
            selected_ids.add(row["word_id"])
            if len(selected) >= count:
                return selected

        remaining = count - len(selected)
        if remaining <= 0:
            return selected

        selected_ids = {word["id"] for word in selected}
        solved_anywhere = solved_word_ids_for_pool(con, user_id, list(pool_by_id)) if scope_id != scope_id_for("errors") else set()
        fresh = [
            word
            for word in pool
            if word["id"] not in selected_ids
            and (word["id"] not in progress or int(progress[word["id"]]["cycle_seen"]) == 0)
            and word["id"] not in solved_anywhere
        ]
        if not fresh:
            con.execute(
                """
                UPDATE word_progress
                SET cycle_seen = 0
                WHERE user_id = ? AND scope_id = ? AND due_reviews = 0
                """,
                (user_id, scope_id),
            )
            fresh = [word for word in pool if word["id"] not in selected_ids]

    random.shuffle(fresh)
    selected.extend(fresh[:remaining])
    return selected


def update_word_progress(
    con: sqlite3.Connection,
    user_id: str,
    scope_id: str,
    word_id: str,
    is_correct: int,
) -> None:
    current = con.execute(
        """
        SELECT due_reviews, correct_count, error_count
        FROM word_progress
        WHERE user_id = ? AND scope_id = ? AND word_id = ?
        """,
        (user_id, scope_id, word_id),
    ).fetchone()
    due_reviews = int(current["due_reviews"]) if current else 0
    correct_count = int(current["correct_count"]) if current else 0
    error_count = int(current["error_count"]) if current else 0

    if is_correct:
        due_reviews = max(due_reviews - 1, 0)
        correct_count += 1
        cycle_seen = 1
    else:
        due_reviews = REPEAT_ON_ERROR
        error_count += 1
        cycle_seen = 0

    con.execute(
        """
        INSERT INTO word_progress
            (user_id, scope_id, word_id, cycle_seen, due_reviews, correct_count, error_count, last_seen_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id, scope_id, word_id) DO UPDATE SET
            cycle_seen = excluded.cycle_seen,
            due_reviews = excluded.due_reviews,
            correct_count = excluded.correct_count,
            error_count = excluded.error_count,
            last_seen_at = excluded.last_seen_at
        """,
        (user_id, scope_id, word_id, cycle_seen, due_reviews, correct_count, error_count, now_iso()),
    )


LINE_PAIRS = {
    "а/о": {"letters": ("а", "о"), "label": "А/О"},
    "и/е": {"letters": ("и", "е"), "label": "И/Е"},
    "и/ы после ц": {"letters": ("и", "ы"), "label": "И/Ы после Ц"},
    "о/ё после шипящих": {"letters": ("о", "ё"), "label": "О/Ё после шипящих"},
}


def line_pair_key(word: dict[str, Any]) -> str | None:
    letter = word["correct_letter"]
    marker = f"{word['category']} {word['rule_name']} {word['dependency']}".lower()
    if "ц" in marker and letter in {"и", "ы"}:
        return "и/ы после ц"
    if "шип" in marker and letter in {"о", "ё"}:
        return "о/ё после шипящих"
    if letter in {"а", "о"}:
        return "а/о"
    if letter in {"и", "е"}:
        return "и/е"
    return None


def line_pair_pools() -> dict[str, dict[str, list[dict[str, Any]]]]:
    pools: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for word in WORDS:
        key = line_pair_key(word)
        if not key:
            continue
        pools.setdefault(key, {}).setdefault(word["correct_letter"], []).append(word)
    return pools


def sample_words(pool: list[dict[str, Any]], count: int, used_ids: set[str]) -> list[dict[str, Any]]:
    fresh = [word for word in pool if word["id"] not in used_ids]
    source = fresh if len(fresh) >= count else pool
    picked = random.sample(source, count)
    used_ids.update(word["id"] for word in picked)
    return picked


def shuffle_line_rows(rows: list[dict[str, Any]]) -> None:
    random.SystemRandom().shuffle(rows)
    if rows and rows[0]["is_correct"] and random.random() < 0.5:
        incorrect_indexes = [index for index, row in enumerate(rows[1:], start=1) if not row["is_correct"]]
        if incorrect_indexes:
            swap_index = random.choice(incorrect_indexes)
            rows[0], rows[swap_index] = rows[swap_index], rows[0]


def make_line_question() -> dict[str, Any]:
    pools = line_pair_pools()
    viable_pairs = [
        pair_key
        for pair_key, by_letter in pools.items()
        if all(len(by_letter.get(letter, [])) >= 3 for letter in LINE_PAIRS[pair_key]["letters"])
    ]
    pair_key = random.choice(viable_pairs)
    letters = LINE_PAIRS[pair_key]["letters"]
    by_letter = pools[pair_key]
    used_ids: set[str] = set()

    rows: list[dict[str, Any]] = []
    correct_row_count = random.choice([2, 3])
    for _ in range(correct_row_count):
        letter = random.choice(letters)
        rows.append(
            {
                "is_correct": True,
                "letter": letter,
                "words": sample_words(by_letter[letter], 3, used_ids),
            }
        )

    for _ in range(5 - correct_row_count):
        first, second = letters
        pattern = random.choice([(first, first, second), (first, second, second)])
        words: list[dict[str, Any]] = []
        for letter in pattern:
            words.extend(sample_words(by_letter[letter], 1, used_ids))
        random.SystemRandom().shuffle(words)
        rows.append({"is_correct": False, "letter": None, "words": words})

    shuffle_line_rows(rows)
    correct_indexes = [str(index + 1) for index, row in enumerate(rows) if row["is_correct"]]
    correct_rows = [row for row in rows if row["is_correct"]]

    return {
        "question_id": secrets.token_hex(8),
        "kind": "line",
        "prompt": "Выберите все строки, где во всех трех словах пропущена одна и та же буква.",
        "rows": [[word["variant"] for word in row["words"]] for row in rows],
        "row_word_ids": [[word["id"] for word in row["words"]] for row in rows],
        "choices": [str(number) for number in range(1, len(rows) + 1)],
        "category": "Строка",
        "rule_id": "line_same_letter",
        "rule_name": f"Строка: {LINE_PAIRS[pair_key]['label']}",
        "explanation": (
            f"В этом варианте работала пара {LINE_PAIRS[pair_key]['label']}. "
            f"Правильные строки: {', '.join(correct_indexes)}."
        ),
        "correct_spelling": "; ".join(
            word["correct_spelling"] for row in correct_rows for word in row["words"]
        ),
        "address": "",
        "_correct_answer": "".join(correct_indexes),
    }


def normalize_given_answer(question: dict[str, Any], value: Any) -> str:
    raw = str(value or "").strip().lower()
    if question.get("kind") == "line":
        return "".join(sorted(char for char in raw if char.isdigit()))
    return raw


def record_attempt(
    con: sqlite3.Connection,
    user_id: str,
    session: dict[str, Any],
    question_id: str,
    question: dict[str, Any],
    given: str,
    elapsed: Any = None,
) -> dict[str, Any]:
    correct = question["correct_answer"].strip().lower()
    is_correct = int(given == correct)
    word_id = question.get("source_word_id")
    if word_id:
        if session["scope_id"] != scope_id_for("errors"):
            update_word_progress(con, user_id, session["scope_id"], word_id, is_correct)
        update_error_bank_progress(con, user_id, word_id, is_correct)
    elif question.get("kind") == "line":
        record_line_word_progress(con, user_id, session, question_id, question, given, is_correct, elapsed)
    con.execute(
        """
        INSERT INTO attempts
            (attempt_id, user_id, mode, scope_id, word_id, rule_id, category, rule_name,
             question_id, prompt, given_answer, correct_answer, is_correct, created_at, time_spent_sec)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            secrets.token_hex(12),
            user_id,
            session["mode"],
            session["scope_id"],
            word_id,
            question.get("rule_id"),
            question.get("category"),
            question.get("rule_name"),
            question_id,
            question.get("prompt"),
            given,
            correct,
            is_correct,
            now_iso(),
            elapsed,
        ),
    )
    return {
        "question_id": question_id,
        "is_correct": bool(is_correct),
        "given_answer": given,
        "correct_answer": correct,
        "explanation": question.get("explanation"),
        "correct_spelling": question.get("correct_spelling"),
    }


def update_error_bank_progress(
    con: sqlite3.Connection,
    user_id: str,
    word_id: str,
    is_correct: int,
) -> None:
    update_word_progress(con, user_id, scope_id_for("errors"), word_id, is_correct)


def record_word_attempt(
    con: sqlite3.Connection,
    user_id: str,
    session: dict[str, Any],
    question_id: str,
    word: dict[str, Any],
    given: str,
    is_correct: int,
    elapsed: Any = None,
) -> None:
    con.execute(
        """
        INSERT INTO attempts
            (attempt_id, user_id, mode, scope_id, word_id, rule_id, category, rule_name,
             question_id, prompt, given_answer, correct_answer, is_correct, created_at, time_spent_sec)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            secrets.token_hex(12),
            user_id,
            session["mode"],
            scope_id_for("errors"),
            word["id"],
            word["rule_id"],
            word["category"],
            word["rule_name"],
            question_id,
            word["variant"],
            given,
            word["correct_letter"],
            is_correct,
            now_iso(),
            elapsed,
        ),
    )


def record_line_word_progress(
    con: sqlite3.Connection,
    user_id: str,
    session: dict[str, Any],
    question_id: str,
    question: dict[str, Any],
    given: str,
    is_correct: int,
    elapsed: Any = None,
) -> None:
    correct_rows = set(question["correct_answer"])
    given_rows = set(given)
    affected_rows = correct_rows.symmetric_difference(given_rows)
    row_word_ids = question.get("row_word_ids") or []
    if is_correct:
        affected_rows = {str(index + 1) for index in range(len(row_word_ids))}

    for row_number in sorted(affected_rows):
        row_index = int(row_number) - 1
        if row_index < 0 or row_index >= len(row_word_ids):
            continue
        for word_id in row_word_ids[row_index]:
            word = WORD_BY_ID.get(word_id)
            if not word:
                continue
            update_word_progress(con, user_id, scope_id_for("line"), word_id, is_correct)
            update_error_bank_progress(con, user_id, word_id, is_correct)
            record_word_attempt(
                con,
                user_id,
                session,
                f"{question_id}:row{row_number}:{word_id}",
                word,
                f"строка {row_number}",
                is_correct,
                elapsed,
            )


def error_bank_words(user_id: str) -> list[dict[str, Any]]:
    with db() as con:
        rows = con.execute(
            """
            SELECT word_id, due_reviews, error_count, last_seen_at
            FROM word_progress
            WHERE user_id = ? AND scope_id = ? AND due_reviews > 0
            ORDER BY due_reviews DESC, error_count DESC, last_seen_at DESC
            """,
            (user_id, scope_id_for("errors")),
        ).fetchall()
    return [WORD_BY_ID[row["word_id"]] for row in rows if row["word_id"] in WORD_BY_ID]


def teacher_dashboard(con: sqlite3.Connection, teacher_id: str) -> dict[str, Any]:
    students = con.execute(
        """
        SELECT u.user_id, u.display_name, u.username, u.email,
               CASE WHEN c.id IS NULL THEN 0 ELSE 1 END AS consent_accepted
        FROM users
        u
        LEFT JOIN user_consents c
          ON c.user_id = u.user_id
         AND c.consent_type = ?
         AND c.document_version = ?
        WHERE u.role = 'student' AND u.teacher_id = ?
        ORDER BY u.display_name
        """,
        (CONSENT_TYPE_PERSONAL_DATA, CURRENT_CONSENT_VERSION, teacher_id),
    ).fetchall()
    result_students = []
    for student in students:
        user_id = student["user_id"]
        summary = con.execute(
            """
            SELECT COUNT(*) AS total, COALESCE(SUM(is_correct), 0) AS correct,
                   COUNT(DISTINCT word_id) AS touched
            FROM attempts
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
        error_rules = con.execute(
            """
            SELECT COALESCE(category, mode) AS category,
                   COALESCE(rule_name, mode) AS rule_name,
                   COUNT(*) AS errors
            FROM attempts
            WHERE user_id = ? AND is_correct = 0
            GROUP BY COALESCE(category, mode), COALESCE(rule_name, mode)
            ORDER BY errors DESC, rule_name
            LIMIT 3
            """,
            (user_id,),
        ).fetchall()
        due_words = con.execute(
            """
            SELECT wp.word_id, wp.due_reviews, wp.error_count
            FROM word_progress wp
            WHERE wp.user_id = ? AND wp.due_reviews > 0
            ORDER BY wp.due_reviews DESC, wp.error_count DESC, wp.last_seen_at DESC
            LIMIT 12
            """,
            (user_id,),
        ).fetchall()
        error_bank = con.execute(
            """
            SELECT word_id, error_count AS errors
            FROM word_progress
            WHERE user_id = ? AND scope_id = ? AND due_reviews > 0
            ORDER BY due_reviews DESC, error_count DESC, last_seen_at DESC
            LIMIT 20
            """,
            (user_id, scope_id_for("errors")),
        ).fetchall()
        category_stats = con.execute(
            """
            SELECT COALESCE(category, mode) AS category,
                   COUNT(*) AS total,
                   COALESCE(SUM(is_correct), 0) AS correct
            FROM attempts
            WHERE user_id = ?
            GROUP BY COALESCE(category, mode)
            ORDER BY category
            """,
            (user_id,),
        ).fetchall()
        recent_attempts = con.execute(
            """
            SELECT created_at, COALESCE(category, mode) AS category,
                   COALESCE(rule_name, mode) AS rule_name,
                   prompt, given_answer, correct_answer, is_correct
            FROM attempts
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 8
            """,
            (user_id,),
        ).fetchall()
        touched = int(summary["touched"] or 0)
        result_students.append(
            {
                "user_id": user_id,
                "display_name": student["display_name"],
                "username": student["username"],
                "email": student["email"],
                "consent_accepted": bool(student["consent_accepted"]),
                "total": int(summary["total"] or 0),
                "correct": int(summary["correct"] or 0),
                "untouched": max(len(WORDS) - touched, 0),
                "not_worked_out": [
                    {
                        "word": WORD_BY_ID[row["word_id"]]["variant"],
                        "correct_spelling": WORD_BY_ID[row["word_id"]]["correct_spelling"],
                        "rule_name": WORD_BY_ID[row["word_id"]]["rule_name"],
                        "due_reviews": int(row["due_reviews"]),
                    }
                    for row in due_words
                    if row["word_id"] in WORD_BY_ID
                ],
                "top_errors": [dict(row) for row in error_rules],
                "category_stats": [dict(row) for row in category_stats],
                "recent_attempts": [dict(row) for row in recent_attempts],
                "error_bank": [
                    {
                        "word": WORD_BY_ID[row["word_id"]]["variant"],
                        "correct_spelling": WORD_BY_ID[row["word_id"]]["correct_spelling"],
                        "rule_name": WORD_BY_ID[row["word_id"]]["rule_name"],
                        "errors": int(row["errors"]),
                    }
                    for row in error_bank
                    if row["word_id"] in WORD_BY_ID
                ],
            }
        )
    return {"students": result_students}


def activity_title_from_scope(scope_id: str | None) -> str:
    scope = scope_id or ""
    if scope.startswith("ege5:"):
        return "ЕГЭ-5"
    if scope.startswith("ege10:"):
        return "ЕГЭ-10"
    if scope.startswith("ege11:"):
        return "ЕГЭ-11"
    if scope.startswith("ege12:"):
        return "ЕГЭ-12"
    if scope.startswith("ege14:"):
        return "ЕГЭ-14"
    return "ЕГЭ-9"


def mode_title(mode: str | None) -> str:
    return {
        "paronym_choice": "Подставь слово",
        "paronym_exam": "Формат ЕГЭ",
        "paronym_tf": "Верно/неверно",
        "rule": "Правило",
        "word_letter": "Слово - буква",
        "mix": "Микс",
        "line": "Строка",
        "errors": "Копилка ошибок",
        "word_context": "Слово в контексте",
        "line_spelling": "Строка",
        "exam": "Формат ЕГЭ",
    }.get(mode or "", mode or "")


def trim_for_admin(value: Any, limit: int = 140) -> str:
    text = str(value or "").strip()
    return text if len(text) <= limit else f"{text[:limit - 1]}…"


def active_visitors_for_admin() -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    result: list[dict[str, Any]] = []
    stale: list[str] = []
    for visitor_id, visitor in ACTIVE_VISITORS.items():
        last_seen = parse_iso(visitor.get("last_seen_at"))
        if not last_seen or (now - last_seen).total_seconds() > ACTIVE_VISITOR_WINDOW_SEC:
            stale.append(visitor_id)
            continue
        result.append({**visitor, "seconds_ago": max(0, int((now - last_seen).total_seconds()))})
    for visitor_id in stale:
        ACTIVE_VISITORS.pop(visitor_id, None)
    result.sort(key=lambda item: item.get("last_seen_at") or "", reverse=True)
    return result


def record_visitor_heartbeat(user: dict[str, Any] | None, payload: dict[str, Any], ip_address: str, user_agent: str) -> dict[str, Any]:
    visitor_id = trim_for_admin(payload.get("visitor_id"), 80) or secrets.token_urlsafe(12)
    now = now_iso()
    ACTIVE_VISITORS[visitor_id] = {
        "visitor_id": visitor_id,
        "user_id": user["user_id"] if user else None,
        "display_name": user["display_name"] if user else "Гость",
        "role": user["role"] if user else "guest",
        "path": trim_for_admin(payload.get("path"), 200) or "/",
        "current_activity": trim_for_admin(payload.get("current_activity"), 60),
        "current_mini_game": trim_for_admin(payload.get("current_mini_game"), 80),
        "last_seen_at": now,
        "ip_address": ip_address,
        "user_agent": trim_for_admin(user_agent, 160),
    }
    return {"ok": True, "visitor_id": visitor_id, "active_seconds": ACTIVE_VISITOR_WINDOW_SEC}


def recent_attempts_for_admin(con: sqlite3.Connection, limit: int = 60) -> list[dict[str, Any]]:
    rows = con.execute(
        """
        SELECT a.created_at, a.mode, a.scope_id, a.category, a.rule_name, a.prompt,
               a.given_answer, a.correct_answer, a.is_correct, a.time_spent_sec,
               u.display_name, u.username, u.email, u.role
        FROM attempts a
        JOIN users u ON u.user_id = a.user_id
        ORDER BY a.created_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [
        {
            **dict(row),
            "activity_title": activity_title_from_scope(row["scope_id"]),
            "mode_title": mode_title(row["mode"]),
            "prompt": trim_for_admin(row["prompt"]),
            "is_correct": bool(row["is_correct"]),
        }
        for row in rows
    ]


def created_games_for_admin(con: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = con.execute(
        """
        SELECT gs.public_id, gs.title, gs.description, gs.mechanic, gs.source_type,
               gs.created_at, gs.updated_at, gs.last_used_at, gs.use_count, gs.is_active,
               gs.deactivated_at, gs.is_deleted, gs.deleted_at, u.display_name AS teacher_name,
               COALESCE(u.email, u.username) AS teacher_email
        FROM game_sets gs
        LEFT JOIN users u ON u.user_id = gs.teacher_id
        ORDER BY COALESCE(gs.last_used_at, gs.created_at) DESC
        """
    ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["is_active"] = bool(row["is_active"])
        item["is_deleted"] = bool(row["is_deleted"])
        item["url"] = public_game_url(row["mechanic"], row["public_id"])
        since = seconds_since(row["last_used_at"] or row["created_at"])
        item["days_since_used"] = None if since is None else since // 86400
        result.append(item)
    return result


def recent_game_visits_for_admin(con: sqlite3.Connection, limit: int = 40) -> list[dict[str, Any]]:
    rows = con.execute(
        """
        SELECT gv.slug, gv.public_id, gv.path, gv.opened_at,
               gs.title AS set_title, gs.mechanic,
               u.display_name AS teacher_name
        FROM game_visits gv
        LEFT JOIN game_sets gs ON gs.public_id = gv.public_id
        LEFT JOIN users u ON u.user_id = gs.teacher_id
        ORDER BY gv.opened_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


def record_public_game_visit(slug: str, public_id: str | None, path: str) -> None:
    with db() as con:
        con.execute(
            """
            INSERT INTO game_visits (slug, public_id, path, opened_at)
            VALUES (?, ?, ?, ?)
            """,
            (slug, public_id, trim_for_admin(path, 240), now_iso()),
        )


def admin_overview(user: dict[str, Any]) -> dict[str, Any]:
    require_admin(user)
    with db() as con:
        platform = con.execute(
            """
            SELECT COUNT(*) AS total, COALESCE(SUM(is_correct), 0) AS correct,
                   COUNT(DISTINCT user_id) AS active_users
            FROM attempts
            """
        ).fetchone()
        teachers = con.execute(
            """
            SELECT t.user_id, t.display_name, t.username, t.email, t.teacher_code, t.password_reset_required,
                   uc.accepted_at AS consent_accepted_at,
                   COUNT(DISTINCT s.user_id) AS students,
                   COUNT(a.attempt_id) AS attempts,
                   COALESCE(SUM(a.is_correct), 0) AS correct
            FROM users t
            LEFT JOIN user_consents uc
                ON uc.user_id = t.user_id
               AND uc.consent_type = ?
               AND uc.document_version = ?
            LEFT JOIN users s ON s.teacher_id = t.user_id AND s.role = 'student'
            LEFT JOIN attempts a ON a.user_id = s.user_id
            WHERE t.role = 'teacher'
            GROUP BY t.user_id
            ORDER BY t.display_name
            """
            ,
            (CONSENT_TYPE_PERSONAL_DATA, CURRENT_CONSENT_VERSION),
        ).fetchall()
        teacher_ids = [row["user_id"] for row in teachers]
        student_rows = []
        if teacher_ids:
            placeholders = ",".join("?" for _ in teacher_ids)
            student_rows = con.execute(
                f"""
                SELECT s.user_id, s.teacher_id, s.display_name, s.username, s.email, s.password_reset_required,
                       uc.accepted_at AS consent_accepted_at,
                       COUNT(a.attempt_id) AS attempts,
                       COALESCE(SUM(a.is_correct), 0) AS correct
                FROM users s
                LEFT JOIN user_consents uc
                    ON uc.user_id = s.user_id
                   AND uc.consent_type = ?
                   AND uc.document_version = ?
                LEFT JOIN attempts a ON a.user_id = s.user_id
                WHERE s.role = 'student' AND s.teacher_id IN ({placeholders})
                GROUP BY s.user_id
                ORDER BY s.display_name
                """,
                (CONSENT_TYPE_PERSONAL_DATA, CURRENT_CONSENT_VERSION, *teacher_ids),
            ).fetchall()
        students_by_teacher: dict[str, list[dict[str, Any]]] = {}
        for row in student_rows:
            item = dict(row)
            item["consent_accepted"] = bool(row["consent_accepted_at"])
            item["consent_version"] = CURRENT_CONSENT_VERSION
            mode_rows = con.execute(
                """
                SELECT mode, COUNT(*) AS attempts, COALESCE(SUM(is_correct), 0) AS correct
                FROM attempts
                WHERE user_id = ?
                GROUP BY mode
                ORDER BY attempts DESC
                """,
                (row["user_id"],),
            ).fetchall()
            item["mode_summary"] = [dict(mode_row) for mode_row in mode_rows]
            students_by_teacher.setdefault(row["teacher_id"], []).append(item)
        recent_attempts = recent_attempts_for_admin(con)
        created_games = created_games_for_admin(con)
        recent_game_visits = recent_game_visits_for_admin(con)
        paid_entities = paid_entities_for_admin(con)
        receipt_orders = receipt_orders_for_admin(con)
        suspicious_users = suspicious_users_for_admin(con)
        total_games = len(created_games)
        active_games = sum(1 for item in created_games if item["is_active"] and not item.get("is_deleted"))
        visible_games = sum(1 for item in created_games if not item.get("is_deleted"))
        opened_games = sum(int(item.get("use_count") or 0) for item in created_games)
    return {
        "platform": dict(platform),
        "online": active_visitors_for_admin(),
        "recent_attempts": recent_attempts,
        "created_games": created_games,
        "recent_game_visits": recent_game_visits,
        "game_stats": {
            "total": visible_games,
            "active": active_games,
            "inactive": visible_games - active_games,
            "deleted": total_games - visible_games,
            "opens": opened_games,
        },
        "paid_entities": paid_entities,
        "receipt_orders": receipt_orders,
        "suspicious_users": suspicious_users,
        "teachers": [
            {
                **dict(row),
                "consent_accepted": bool(row["consent_accepted_at"]),
                "consent_version": CURRENT_CONSENT_VERSION,
                "students_list": students_by_teacher.get(row["user_id"], []),
            }
            for row in teachers
        ],
    }


def suspicious_users_for_admin(con: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = con.execute(
        """
        SELECT user_id, display_name, username, email, role, created_at
        FROM users
        WHERE role != 'admin'
          AND (
            LOWER(COALESCE(email, username, '')) LIKE 'bot%@test.ru'
            OR LOWER(COALESCE(email, username, '')) IN ('xss_test@test.ru', 'audit_test_ege@test.ru')
            OR LOWER(COALESCE(email, username, '')) LIKE '%<script%'
            OR LOWER(COALESCE(username, '')) LIKE '%<script%'
            OR LOWER(COALESCE(email, username, '')) LIKE '%@test.ru'
          )
        ORDER BY created_at DESC
        LIMIT 200
        """
    ).fetchall()
    return [dict(row) for row in rows]


def delete_user_records(con: sqlite3.Connection, user_id: str) -> None:
    con.execute("DELETE FROM attempts WHERE user_id = ?", (user_id,))
    con.execute("DELETE FROM word_progress WHERE user_id = ?", (user_id,))
    con.execute("DELETE FROM password_reset_tokens WHERE user_id = ?", (user_id,))
    con.execute("DELETE FROM user_consents WHERE user_id = ?", (user_id,))
    con.execute("DELETE FROM users WHERE user_id = ?", (user_id,))


def delete_user_for_admin(admin: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    require_admin(admin)
    user_id = str(payload.get("user_id") or "").strip()
    if not user_id or user_id == admin["user_id"]:
        raise ValueError("Нельзя удалить этого пользователя.")
    with db() as con:
        row = con.execute("SELECT user_id, username, email, display_name, role FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if not row:
            raise ValueError("Пользователь не найден.")
        if row["role"] == "admin":
            raise ValueError("Администраторов нельзя удалить через эту кнопку.")
        delete_user_records(con, user_id)
    for token, session in list(SESSIONS.items()):
        if session.get("user", {}).get("user_id") == user_id:
            SESSIONS.pop(token, None)
    return {"ok": True, "deleted": [dict(row)]}


def delete_suspicious_users_for_admin(admin: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    require_admin(admin)
    if payload.get("confirm") is not True:
        raise ValueError("Подтвердите удаление подозрительных пользователей.")
    with db() as con:
        rows = suspicious_users_for_admin(con)
        for row in rows:
            delete_user_records(con, row["user_id"])
    deleted_ids = {row["user_id"] for row in rows}
    for token, session in list(SESSIONS.items()):
        if session.get("user", {}).get("user_id") in deleted_ids:
            SESSIONS.pop(token, None)
    return {"ok": True, "deleted": rows, "count": len(rows)}


def start_practice(user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    mode = payload.get("mode")
    count = max(1, min(int(payload.get("count") or 10), 30))
    if mode in {"rule", "word_letter"}:
        raw_rule_ids = payload.get("rule_ids")
        if isinstance(raw_rule_ids, list):
            rule_ids = [str(rule_id) for rule_id in raw_rule_ids if str(rule_id) in WORDS_BY_RULE]
        else:
            rule_id = str(payload.get("rule_id") or "")
            rule_ids = [rule_id] if rule_id in WORDS_BY_RULE else []
        rule_ids = list(dict.fromkeys(rule_ids))

        pool: list[dict[str, Any]] = []
        for rule_id in rule_ids:
            pool.extend(WORDS_BY_RULE.get(rule_id, []))
        if not pool:
            raise ValueError("Выберите хотя бы одну подгруппу с заданиями.")
        scope_id = scope_id_for(mode, rule_ids=rule_ids)
        questions = [make_word_question(word) for word in pick_words_for_scope(user["user_id"], scope_id, pool, min(count, len(pool)))]
    elif mode == "mix":
        scope_id = scope_id_for(mode)
        questions = [make_word_question(word) for word in pick_words_for_scope(user["user_id"], scope_id, WORDS, min(count, len(WORDS)))]
    elif mode == "line":
        scope_id = scope_id_for(mode)
        questions = [make_line_question() for _ in range(count)]
    elif mode == "errors":
        scope_id = scope_id_for(mode)
        pool = error_bank_words(user["user_id"])
        if not pool:
            raise ValueError("Копилка ошибок пока пуста.")
        questions = [make_word_question(word) for word in pick_words_for_scope(user["user_id"], scope_id, pool, min(count, len(pool)))]
    else:
        raise ValueError("Неизвестный режим тренировки.")

    session_id = secrets.token_hex(12)
    answer_key: dict[str, dict[str, Any]] = {}
    public_questions = []
    for question in questions:
        correct_answer = question.pop("_correct_answer", "")
        answer_key[question["question_id"]] = {**question, "correct_answer": str(correct_answer).lower()}
        question.pop("row_word_ids", None)
        public_questions.append(question)

    PRACTICE_SESSIONS[session_id] = {
        "user_id": user["user_id"],
        "mode": mode,
        "scope_id": scope_id,
        "started_at": now_iso(),
        "questions": answer_key,
        "answered": {},
    }
    return {"session_id": session_id, "questions": public_questions}


def check_practice_answer(user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    session_id = payload.get("session_id")
    question_id = str(payload.get("question_id") or "")
    session = PRACTICE_SESSIONS.get(session_id)
    if not session or session["user_id"] != user["user_id"]:
        raise ValueError("Сессия тренировки не найдена.")
    question = session["questions"].get(question_id)
    if not question:
        raise ValueError("Вопрос не найден.")
    if question_id in session["answered"]:
        return session["answered"][question_id]
    given = normalize_given_answer(question, payload.get("answer", ""))
    with db() as con:
        result = record_attempt(con, user["user_id"], session, question_id, question, given, payload.get("time_spent_sec"))
    session["answered"][question_id] = result
    if len(session["answered"]) >= len(session["questions"]):
        PRACTICE_SESSIONS.pop(session_id, None)
    return result


def submit_practice(user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    session_id = payload.get("session_id")
    answers = payload.get("answers") or {}
    elapsed = payload.get("time_spent_sec")
    session = PRACTICE_SESSIONS.get(session_id)
    if not session or session["user_id"] != user["user_id"]:
        raise ValueError("Сессия тренировки не найдена.")

    results = []
    with db() as con:
        for question_id, question in session["questions"].items():
            if question_id in session.get("answered", {}):
                results.append(session["answered"][question_id])
                continue
            given = normalize_given_answer(question, answers.get(question_id, ""))
            results.append(record_attempt(con, user["user_id"], session, question_id, question, given, elapsed))
    PRACTICE_SESSIONS.pop(session_id, None)
    return {
        "results": results,
        "correct": sum(1 for result in results if result["is_correct"]),
        "total": len(results),
    }


def progress_for(user: dict[str, Any]) -> dict[str, Any]:
    with db() as con:
        params: tuple[Any, ...] = ()
        where = ""
        if user["role"] != "teacher":
            where = "WHERE a.user_id = ?"
            params = (user["user_id"],)
        else:
            where = "WHERE a.user_id IN (SELECT user_id FROM users WHERE role = 'student' AND teacher_id = ?)"
            params = (user["user_id"],)
        summary = con.execute(
            f"""
            SELECT COUNT(*) AS total, COALESCE(SUM(is_correct), 0) AS correct
            FROM attempts a
            {where}
            """,
            params,
        ).fetchone()
        by_student = con.execute(
            """
            SELECT u.display_name, u.username, COUNT(a.attempt_id) AS total,
                   COALESCE(SUM(a.is_correct), 0) AS correct
            FROM users u
            LEFT JOIN attempts a ON a.user_id = u.user_id
            WHERE u.role = 'student'
              AND (
                (? = 'teacher' AND u.teacher_id = ?)
                OR (? = 'student' AND u.user_id = ?)
              )
            GROUP BY u.user_id
            ORDER BY u.display_name
            """,
            (user["role"], user["user_id"], user["role"], user["user_id"]),
        ).fetchall()
        by_rule = con.execute(
            f"""
            SELECT COALESCE(a.category, a.mode) AS category,
                   COALESCE(a.rule_name, a.mode) AS rule_name,
                   COUNT(*) AS total,
                   COALESCE(SUM(a.is_correct), 0) AS correct
            FROM attempts a
            {where}
            GROUP BY COALESCE(a.category, a.mode), COALESCE(a.rule_name, a.mode)
            ORDER BY category, rule_name
            """,
            params,
        ).fetchall()
        by_category = con.execute(
            f"""
            SELECT COALESCE(a.category, a.mode) AS category, COUNT(*) AS total,
                   COALESCE(SUM(a.is_correct), 0) AS correct
            FROM attempts a
            {where}
            GROUP BY COALESCE(a.category, a.mode)
            ORDER BY category
            """,
            params,
        ).fetchall()
        recent = con.execute(
            f"""
            SELECT a.created_at, a.mode, a.category, a.rule_name, a.prompt, a.given_answer,
                   a.correct_answer, a.is_correct, u.display_name
            FROM attempts a
            JOIN users u ON u.user_id = a.user_id
            {where}
            ORDER BY a.created_at DESC
            LIMIT 20
            """,
            params,
        ).fetchall()
        answer_lists = con.execute(
            f"""
            SELECT a.created_at, a.category, a.rule_name, a.prompt, a.given_answer,
                   a.correct_answer, a.is_correct, u.display_name
            FROM attempts a
            JOIN users u ON u.user_id = a.user_id
            {where}
            ORDER BY a.created_at DESC
            LIMIT 80
            """,
            params,
        ).fetchall()
        due = con.execute(
            """
            SELECT COUNT(*) AS due
            FROM word_progress
            WHERE user_id = ? AND due_reviews > 0
            """,
            (user["user_id"],),
        ).fetchone() if user["role"] != "teacher" else {"due": 0}
        error_bank = con.execute(
            """
            SELECT COUNT(*) AS total
            FROM word_progress
            WHERE user_id = ? AND scope_id = ? AND due_reviews > 0
            """,
            (user["user_id"], scope_id_for("errors")),
        ).fetchone() if user["role"] != "teacher" else {"total": 0}
    return {
        "summary": dict(summary),
        "due_reviews": int(due["due"]),
        "error_bank_count": int(error_bank["total"]),
        "teacher_dashboard": teacher_dashboard(con, user["user_id"]) if user["role"] == "teacher" else None,
        "by_student": [dict(row) for row in by_student],
        "by_category": [dict(row) for row in by_category],
        "by_rule": [dict(row) for row in by_rule],
        "recent": [dict(row) for row in recent],
        "correct_attempts": [dict(row) for row in answer_lists if int(row["is_correct"]) == 1],
        "incorrect_attempts": [dict(row) for row in answer_lists if int(row["is_correct"]) == 0],
    }


def require_teacher(user: dict[str, Any]) -> None:
    if user["role"] != "teacher":
        raise PermissionError("Функция доступна только учителю.")


def require_teacher_or_admin(user: dict[str, Any]) -> None:
    if user["role"] not in {"teacher", "admin"}:
        raise PermissionError("Функция доступна только учителю или администратору.")


def game_source_config(source: str) -> dict[str, Any]:
    sources = {
        "ege9": {
            "title": "ЕГЭ-9",
            "rules": RULES,
            "words_by_rule": WORDS_BY_RULE,
            "letter_choices": letter_choices,
        },
        "ege10": {
            "title": "ЕГЭ-10",
            "rules": ege10_module.RULES,
            "words_by_rule": ege10_module.WORDS_BY_RULE,
            "letter_choices": ege10_module.letter_choices,
        },
        "ege11": {
            "title": "ЕГЭ-11",
            "rules": ege11_module.RULES,
            "words_by_rule": ege11_module.WORDS_BY_RULE,
            "letter_choices": ege11_module.letter_choices,
        },
        "ege12": {
            "title": "ЕГЭ-12",
            "rules": ege12_module.RULES,
            "words_by_rule": ege12_module.WORDS_BY_RULE,
            "letter_choices": ege12_module.letter_choices,
        },
    }
    if source not in sources:
        raise ValueError("Источник заданий не найден.")
    return sources[source]


def public_game_url(mechanic: str, public_id: str) -> str:
    return f"{APP_BASE_URL}/games/{mechanic}?set={public_id}"


def make_game_public_id(con: sqlite3.Connection) -> str:
    for _ in range(20):
        public_id = secrets.token_urlsafe(8).replace("-", "").replace("_", "")
        exists = con.execute("SELECT 1 FROM game_sets WHERE public_id = ?", (public_id,)).fetchone()
        if not exists:
            return public_id
    raise RuntimeError("Не удалось создать уникальную ссылку.")


def clean_game_string(value: Any, limit: int = GAME_SET_MAX_STRING) -> str:
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(value or "").strip())
    text = text.replace("</script", "<\\/script")
    return text[:limit]


def generic_game_options(answer: str) -> list[str]:
    answer = clean_game_string(answer, 20).lower()
    groups = [
        ["а", "о"],
        ["е", "и"],
        ["е", "ё", "о"],
        ["ь", "ъ", "-"],
        ["и", "ы"],
    ]
    for group in groups:
        if answer in group:
            return group
    return [answer] if answer else []


def normalize_game_options(options: Any, answer: str) -> list[str]:
    result: list[str] = []
    if isinstance(options, list):
        for option in options:
            text = clean_game_string(option, 80)
            if text and text not in result:
                result.append(text)
            if len(result) >= 6:
                break
    if not result:
        result = generic_game_options(answer)
    answer_text = clean_game_string(answer, 80)
    if answer_text and answer_text not in result:
        result.insert(0, answer_text)
    return result[:6]


def normalize_game_answer(value: Any) -> str:
    answer = clean_game_string(value, 80).lower()
    return {"e": "е", "i": "и"}.get(answer, answer)


def normalize_game_item(item: Any, index: int) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ValueError(f"Задание {index}: ожидается объект.")
    variant = clean_game_string(item.get("variant") or item.get("prompt") or item.get("text"))
    answer = normalize_game_answer(item.get("answer") or item.get("correct_letter") or item.get("correct"))
    if not variant:
        raise ValueError(f"Задание {index}: нет поля variant.")
    if not answer:
        raise ValueError(f"Задание {index}: нет поля answer.")
    return {
        "variant": variant,
        "answer": answer,
        "options": normalize_game_options(item.get("options") or item.get("choices"), answer),
        "correct_spelling": clean_game_string(item.get("correct_spelling")),
        "explanation": clean_game_string(item.get("explanation")),
    }


def normalize_game_payload(payload: Any, default_mechanic: str = "fluffs") -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("JSON должен быть объектом.")
    mechanic = clean_game_string(payload.get("mechanic") or default_mechanic, 40) or default_mechanic
    if mechanic not in GAME_MECHANICS:
        raise ValueError("Выбранная механика пока недоступна.")
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("Поле items должно быть непустым массивом.")
    if len(items) > GAME_SET_MAX_ITEMS:
        raise ValueError(f"В одном наборе можно сохранить не больше {GAME_SET_MAX_ITEMS} заданий.")
    title = clean_game_string(payload.get("title"), 120)
    if not title:
        raise ValueError("Нужно указать title.")
    normalized_items = [normalize_game_item(item, index + 1) for index, item in enumerate(items)]
    if mechanic == "berry-season":
        bad_answers = [item["answer"] for item in normalized_items if item["answer"] not in {"е", "и"}]
        if bad_answers:
            raise ValueError("Для «Ягодного сезона» подходят только ответы «е» и «и».")
    return {
        "title": title,
        "description": clean_game_string(payload.get("description"), 300),
        "mechanic": mechanic,
        "items": normalized_items,
    }


def game_sources_for_teacher() -> dict[str, Any]:
    sources = []
    for source_id in ("ege9", "ege10", "ege11", "ege12"):
        config = game_source_config(source_id)
        grouped: dict[str, list[dict[str, Any]]] = {}
        for rule in config["rules"]:
            grouped.setdefault(rule["category"], []).append(rule)
        sources.append(
            {
                "id": source_id,
                "title": config["title"],
                "rules": grouped,
            }
        )
    return {
        "mechanics": [
            {"id": "fluffs", "title": "Пушинки", "available": True},
            {"id": "berry-season", "title": "Ягодный сезон: ИК-ЕК", "available": True},
            {"id": "mouse-space", "title": "Мышонок в космосе: выбор буквы", "available": True},
            {"id": "focus", "title": "Фокус", "available": False},
        ],
        "sources": sources,
    }


def game_item_from_word(word: dict[str, Any], choices_func: Any) -> dict[str, Any]:
    answer = normalize_game_answer(word.get("correct_letter") or word.get("answer"))
    return {
        "variant": clean_game_string(word.get("variant")),
        "answer": answer,
        "options": normalize_game_options(choices_func(word), answer),
        "correct_spelling": clean_game_string(word.get("correct_spelling")),
        "explanation": clean_game_string(word.get("explanation")),
    }


def save_game_set(
    con: sqlite3.Connection,
    user: dict[str, Any],
    payload: dict[str, Any],
    source_type: str,
) -> dict[str, Any]:
    public_id = make_game_public_id(con)
    created_at = now_iso()
    con.execute(
        """
        INSERT INTO game_sets
            (id, public_id, teacher_id, title, description, mechanic, source_type,
             payload_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            secrets.token_hex(12),
            public_id,
            user["user_id"],
            payload["title"],
            payload.get("description") or "",
            payload["mechanic"],
            source_type,
            json.dumps(payload, ensure_ascii=False),
            created_at,
            created_at,
        ),
    )
    return {
        "public_id": public_id,
        "url": public_game_url(payload["mechanic"], public_id),
        "title": payload["title"],
        "description": payload.get("description") or "",
        "mechanic": payload["mechanic"],
        "items_count": len(payload["items"]),
    }


def create_game_set_from_base(user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    require_teacher_or_admin(user)
    mechanic = clean_game_string(payload.get("mechanic") or "fluffs", 40)
    if mechanic not in GAME_MECHANICS:
        raise ValueError("Выбранная механика пока недоступна.")
    source = clean_game_string(payload.get("source") or "ege9", 20)
    raw_rule_ids = payload.get("rule_ids")
    if isinstance(raw_rule_ids, list):
        rule_ids = [clean_game_string(rule_id, 80) for rule_id in raw_rule_ids]
    else:
        rule_ids = [clean_game_string(payload.get("rule_id"), 80)]
    rule_ids = list(dict.fromkeys(rule_id for rule_id in rule_ids if rule_id))
    if not rule_ids:
        raise ValueError("Выберите рубрику.")
    count = int(payload.get("count") or 10)
    count = max(1, min(count, GAME_SET_MAX_ITEMS))
    config = game_source_config(source)
    pool: list[dict[str, Any]] = []
    for rule_id in rule_ids:
        pool.extend(config["words_by_rule"].get(rule_id, []))
    if not pool:
        raise ValueError("В выбранных рубриках нет заданий.")
    random.shuffle(pool)
    items = [game_item_from_word(word, config["letter_choices"]) for word in pool]
    if mechanic == "berry-season":
        items = [item for item in items if item["answer"] in {"е", "и"}]
    items = items[:count]
    if not items:
        raise ValueError("В выбранных рубриках нет заданий для этой механики.")
    selected_rules = [item for item in config["rules"] if item["rule_id"] in set(rule_ids)]
    default_title = selected_rules[0]["rule_name"] if len(selected_rules) == 1 else f"{len(selected_rules)} рубрики"
    mechanic_title = {
        "berry-season": "Ягодный сезон",
        "mouse-space": "Мышонок в космосе",
    }.get(mechanic, "Пушинки")
    title = clean_game_string(payload.get("title"), 120) or f"{mechanic_title}: {default_title}"
    game_payload = normalize_game_payload(
        {
            "title": title,
            "description": clean_game_string(payload.get("description"), 300),
            "mechanic": mechanic,
            "items": items,
        }
    )
    with db() as con:
        return save_game_set(con, user, game_payload, "from_base")


def create_game_set_from_upload(user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    require_teacher_or_admin(user)
    raw_payload = payload.get("payload", payload)
    encoded = json.dumps(raw_payload, ensure_ascii=False).encode("utf-8")
    if len(encoded) > GAME_SET_MAX_PAYLOAD_BYTES:
        raise ValueError("JSON слишком большой.")
    game_payload = normalize_game_payload(raw_payload)
    with db() as con:
        return save_game_set(con, user, game_payload, "uploaded_json")


def public_game_set(public_id: str) -> dict[str, Any]:
    with db() as con:
        row = con.execute(
            """
            SELECT title, description, mechanic, payload_json, is_active, is_deleted
            FROM game_sets
            WHERE public_id = ?
            """,
            (public_id,),
        ).fetchone()
        if not row:
            raise LookupError("Набор не найден или ссылка устарела.")
        if int(row["is_deleted"] or 0):
            raise PermissionError("Эта игра больше недоступна.")
        if not int(row["is_active"] or 0):
            raise PermissionError("Эта игра деактивирована администратором.")
        con.execute(
            """
            UPDATE game_sets
            SET last_used_at = ?, use_count = COALESCE(use_count, 0) + 1
            WHERE public_id = ?
            """,
            (now_iso(), public_id),
        )
        payload = json.loads(row["payload_json"])
    return {
        "title": row["title"],
        "description": row["description"] or "",
        "mechanic": row["mechanic"],
        "items": payload.get("items", []),
    }


def toggle_admin_game(user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    require_admin(user)
    public_id = trim_for_admin(payload.get("public_id"), 80)
    is_active = 1 if payload.get("is_active") else 0
    if not public_id:
        raise ValueError("Не указана игра.")
    with db() as con:
        row = con.execute("SELECT public_id, title, mechanic FROM game_sets WHERE public_id = ?", (public_id,)).fetchone()
        if not row:
            raise LookupError("Игра не найдена.")
        if is_active:
            con.execute(
                """
                UPDATE game_sets
                SET is_active = 1, deactivated_at = NULL, deactivated_by = NULL, updated_at = ?
                WHERE public_id = ?
                """,
                (now_iso(), public_id),
            )
        else:
            con.execute(
                """
                UPDATE game_sets
                SET is_active = 0, deactivated_at = ?, deactivated_by = ?, updated_at = ?
                WHERE public_id = ?
                """,
                (now_iso(), user["user_id"], now_iso(), public_id),
            )
    return {
        "ok": True,
        "public_id": public_id,
        "is_active": bool(is_active),
        "url": public_game_url(row["mechanic"], public_id),
    }


def soft_delete_game(user: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    require_teacher_or_admin(user)
    public_id = trim_for_admin(payload.get("public_id"), 80)
    if not public_id:
        raise ValueError("Не указана игра.")
    with db() as con:
        row = con.execute(
            "SELECT public_id, title, mechanic, teacher_id, is_deleted FROM game_sets WHERE public_id = ?",
            (public_id,),
        ).fetchone()
        if not row:
            raise LookupError("Игра не найдена.")
        if user["role"] != "admin" and row["teacher_id"] != user["user_id"]:
            raise PermissionError("Можно удалить только свою созданную игру.")
        if int(row["is_deleted"] or 0):
            return {"ok": True, "public_id": public_id, "is_deleted": True}
        con.execute(
            """
            UPDATE game_sets
            SET is_deleted = 1, deleted_at = ?, deleted_by = ?, updated_at = ?
            WHERE public_id = ?
            """,
            (now_iso(), user["user_id"], now_iso(), public_id),
        )
    return {"ok": True, "public_id": public_id, "is_deleted": True}


def csv_bytes(rows: list[dict[str, Any]], headers: list[tuple[str, str]]) -> bytes:
    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.writer(output, delimiter=";")
    writer.writerow([title for _, title in headers])
    for row in rows:
        writer.writerow([row.get(key, "") for key, _ in headers])
    return output.getvalue().encode("utf-8")


def progress_export(user: dict[str, Any], section: str) -> tuple[bytes, str, str]:
    data = progress_for(user)
    if section == "students":
        rows = [
            {
                "name": row["display_name"],
                "username": row["username"],
                "total": row["total"],
                "correct": row["correct"],
                "accuracy": f"{round((row['correct'] / row['total']) * 100) if row['total'] else 0}%",
            }
            for row in data["by_student"]
        ]
        headers = [("name", "Имя"), ("username", "Логин"), ("total", "Ответов"), ("correct", "Верно"), ("accuracy", "Точность")]
    elif section == "categories":
        rows = data["by_category"]
        headers = [("category", "Группа"), ("total", "Ответов"), ("correct", "Верно")]
    elif section == "rules":
        rows = data["by_rule"]
        headers = [("category", "Группа"), ("rule_name", "Подгруппа"), ("total", "Ответов"), ("correct", "Верно")]
    elif section == "correct":
        rows = data["correct_attempts"]
        headers = [("display_name", "Ученик"), ("category", "Группа"), ("rule_name", "Подгруппа"), ("prompt", "Задание"), ("given_answer", "Ответ"), ("correct_answer", "Правильно")]
    elif section == "incorrect":
        rows = data["incorrect_attempts"]
        headers = [("display_name", "Ученик"), ("category", "Группа"), ("rule_name", "Подгруппа"), ("prompt", "Задание"), ("given_answer", "Ответ"), ("correct_answer", "Правильно")]
    else:
        rows = data["recent"]
        headers = [("created_at", "Дата"), ("display_name", "Пользователь"), ("category", "Группа"), ("rule_name", "Подгруппа"), ("prompt", "Задание"), ("given_answer", "Ответ"), ("correct_answer", "Правильно"), ("is_correct", "Верно")]
    filename = f"ege_statistics_{section}.csv"
    return csv_bytes(rows, headers), filename, "text/csv; charset=utf-8"


def teacher_error_pool(teacher_id: str) -> list[dict[str, Any]]:
    with db() as con:
        rows = con.execute(
            """
            SELECT wp.word_id
            FROM word_progress wp
            JOIN users u ON u.user_id = wp.user_id
            WHERE u.teacher_id = ? AND wp.scope_id = ? AND wp.due_reviews > 0
            GROUP BY wp.word_id
            ORDER BY MAX(wp.due_reviews) DESC, MAX(wp.error_count) DESC, MAX(wp.last_seen_at) DESC
            """,
            (teacher_id, scope_id_for("errors")),
        ).fetchall()
    return [WORD_BY_ID[row["word_id"]] for row in rows if row["word_id"] in WORD_BY_ID]


def test_words_for_payload(user: dict[str, Any], payload: dict[str, Any], count: int) -> tuple[str, list[dict[str, Any]]]:
    mode = str(payload.get("mode") or "rule")
    include_errors = bool(payload.get("include_errors"))
    pool: list[dict[str, Any]] = []
    if mode == "rule":
        rule_ids = [str(rule_id) for rule_id in payload.get("rule_ids", []) if str(rule_id) in WORDS_BY_RULE]
        for rule_id in dict.fromkeys(rule_ids):
            pool.extend(WORDS_BY_RULE[rule_id])
        title = "Тест по выбранным темам"
    elif mode == "mix":
        pool = list(WORDS)
        title = "Смешанный тест"
    elif mode == "errors":
        pool = teacher_error_pool(user["user_id"])
        title = "Тест по копилке ошибок"
    else:
        raise ValueError("Для файла выберите режим: темы, микс или копилка ошибок.")
    if include_errors and mode != "errors":
        seen = {word["id"] for word in pool}
        pool.extend(word for word in teacher_error_pool(user["user_id"]) if word["id"] not in seen)
    if not pool:
        raise ValueError("Нет слов для составления теста.")
    random.shuffle(pool)
    return title, pool[: min(count, len(pool))]


def build_test_file(user: dict[str, Any], payload: dict[str, Any]) -> tuple[bytes, str, str]:
    require_teacher(user)
    activity = str(payload.get("activity") or "ege9")
    if activity == "ege10":
        return ege10_module.build_test_file(user, payload)
    if activity == "ege11":
        return ege11_module.build_test_file(user, payload)
    if activity == "ege12":
        return ege12_module.build_test_file(user, payload)
    if activity == "ege13":
        return ege13_module.build_test_file(user, payload)
    if activity == "ege14":
        return ege14_module.build_test_file(user, payload)
    if activity == "ege15":
        return ege15_module.build_test_file(user, payload)
    if activity == "orthography-ege":
        return ege_orthography_module.build_test_file(user, payload)
    if activity == "ege5":
        return build_ege5_test_file(user, payload)
    if activity != "ege9":
        raise ValueError("Для этого раздела составление теста недоступно.")
    count = max(1, min(int(payload.get("count") or 10), 60))
    mode = str(payload.get("mode") or "rule")
    lines = [f"Тест: {now_iso()}", ""]
    answers = ["Ответы", ""]
    if mode == "line":
        for index in range(1, count + 1):
            question = make_line_question()
            lines.append(f"{index}. {question['prompt']}")
            for row_index, row in enumerate(question["rows"], start=1):
                lines.append(f"   {row_index}) {', '.join(row)}")
            lines.append("")
            answers.append(f"{index}. {question['_correct_answer']} — {question['correct_spelling']}")
        filename = "ege_test_lines.txt"
    else:
        title, words = test_words_for_payload(user, payload, count)
        lines[0] = f"{title}: {now_iso()}"
        for index, word in enumerate(words, start=1):
            lines.append(f"{index}. {word['variant']}")
            answers.append(f"{index}. {word['correct_letter']} — {word['correct_spelling']} ({word['rule_name']})")
        filename = "ege_test.txt"
    body = "\n".join(lines + ["", ""] + answers) + "\n"
    return body.encode("utf-8"), filename, "text/plain; charset=utf-8"


class Ege9OrthographyHandler:
    start_practice = staticmethod(start_practice)
    submit_practice = staticmethod(submit_practice)
    check_practice_answer = staticmethod(check_practice_answer)
    build_test_file = staticmethod(build_test_file)


ege_orthography_module.set_ege9_handler(Ege9OrthographyHandler)


def ege5_teacher_error_rows(teacher_id: str) -> list[dict[str, Any]]:
    with db() as con:
        rows = con.execute(
            """
            SELECT wp.word_id
            FROM word_progress wp
            JOIN users u ON u.user_id = wp.user_id
            WHERE u.teacher_id = ? AND wp.scope_id = ? AND wp.due_reviews > 0
            GROUP BY wp.word_id
            ORDER BY MAX(wp.due_reviews) DESC, MAX(wp.error_count) DESC, MAX(wp.last_seen_at) DESC
            """,
            (teacher_id, ege5_module.scope_id_for("errors")),
        ).fetchall()
    pool: list[dict[str, Any]] = []
    for row in rows:
        group_rows = ege5_module.ROWS_BY_GROUP.get(row["word_id"], [])
        if group_rows:
            pool.append(random.choice(group_rows))
    return pool


def ege5_test_rows_for_payload(user: dict[str, Any], payload: dict[str, Any], count: int) -> tuple[str, list[dict[str, Any]]]:
    mode = str(payload.get("mode") or "paronym_exam")
    pool: list[dict[str, Any]] = []
    if mode == "paronym_choice":
        rule_ids = [str(rule_id) for rule_id in payload.get("rule_ids", []) if str(rule_id) in ege5_module.ROWS_BY_GROUP]
        for rule_id in dict.fromkeys(rule_ids):
            pool.extend(ege5_module.ROWS_BY_GROUP[rule_id])
        title = "Тест по выбранным группам паронимов"
    elif mode == "errors":
        pool = ege5_teacher_error_rows(user["user_id"])
        title = "Тест по копилке ошибок: паронимы"
    elif mode == "paronym_exam":
        pool = list(ege5_module.ERROR_ROWS)
        title = "ЕГЭ. Задание 5: паронимы"
    else:
        raise ValueError("Для паронимов выберите режим: формат ЕГЭ, выбранные группы или копилка ошибок.")
    if bool(payload.get("include_errors")) and mode != "errors":
        seen = {row["id"] for row in pool}
        pool.extend(row for row in ege5_teacher_error_rows(user["user_id"]) if row["id"] not in seen)
    if not pool:
        raise ValueError("Нет строк для составления теста.")
    random.shuffle(pool)
    return title, pool[: min(count, len(pool))]


def build_ege5_test_file(user: dict[str, Any], payload: dict[str, Any]) -> tuple[bytes, str, str]:
    count = max(1, min(int(payload.get("count") or 10), 60))
    mode = str(payload.get("mode") or "paronym_exam")
    lines = [f"ЕГЭ. Задание 5: {now_iso()}", ""]
    answers = ["Ответы", ""]
    if mode == "paronym_exam":
        lines[0] = f"ЕГЭ. Задание 5: паронимы: {now_iso()}"
        for index in range(1, count + 1):
            question = ege5_module.make_exam_question()
            lines.append(f"{index}. {question['prompt']}")
            for row_index, row in enumerate(question["rows"], start=1):
                lines.append(f"   {row_index}) {row['sentence']}")
            correct_row, _, correct_word = str(question["_correct_answer"]).partition("|")
            lines.append("")
            answers.append(f"{index}. строка {correct_row}, правильно: {correct_word}")
        filename = "ege5_paronyms_exam.txt"
    else:
        title, rows = ege5_test_rows_for_payload(user, payload, count)
        lines[0] = f"{title}: {now_iso()}"
        for index, row in enumerate(rows, start=1):
            prompt = ege5_module.sentence_with_blank(row)
            choices = ege5_module.choices_for(row)
            lines.append(f"{index}. {prompt}")
            if choices:
                lines.append(f"   Варианты: {', '.join(choices)}")
            lines.append("")
            answers.append(f"{index}. {row['correct_word']} ({row['rule_name']})")
        filename = "ege5_paronyms_test.txt"
    body = "\n".join(lines + ["", ""] + answers) + "\n"
    return body.encode("utf-8"), filename, "text/plain; charset=utf-8"


def reset_user_password(admin: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    require_admin(admin)
    user_id = str(payload.get("user_id") or "")
    if not user_id or user_id == admin["user_id"]:
        raise ValueError("Нельзя сбросить пароль этому пользователю.")
    with db() as con:
        row = con.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if not row:
            raise ValueError("Пользователь не найден.")
        salt = secrets.token_hex(16)
        con.execute(
            """
            UPDATE users
            SET password_salt = ?,
                password_hash = ?,
                password_reset_required = 1
            WHERE user_id = ?
            """,
            (salt, password_hash(secrets.token_urlsafe(32), salt), user_id),
        )
    return {"ok": True, "username": row["username"]}


def paid_entities_for_admin(con: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = con.execute(
        """
        SELECT product_id, slug, title, type, amount, currency, delivery_url, cover_url,
               is_active, updated_at
        FROM paid_entities
        ORDER BY CASE type WHEN 'product' THEN 0 ELSE 1 END, amount + 0, title
        """
    ).fetchall()
    return [
        {
            **dict(row),
            "is_active": bool(row["is_active"]),
            "has_delivery_url": bool(str(row["delivery_url"] or "").strip()),
            "has_cover_url": bool(str(row["cover_url"] or "").strip()),
        }
        for row in rows
    ]


def shop_products_public() -> dict[str, Any]:
    with db() as con:
        rows = con.execute(
            """
            SELECT slug, title, type, amount, currency, cover_url, is_active
            FROM paid_entities
            WHERE is_active = 1
            ORDER BY CASE type WHEN 'product' THEN 0 ELSE 1 END, amount + 0, title
            """
        ).fetchall()
    return {
        "products": [
            {
                "slug": row["slug"],
                "title": row["title"],
                "type": row["type"],
                "amount": row["amount"],
                "currency": row["currency"],
                "price": format_amount_label(row["amount"], row["currency"]),
                "cover_url": row["cover_url"] or "",
                "is_active": bool(row["is_active"]),
            }
            for row in rows
        ]
    }


def format_amount_label(amount: str, currency: str = "RUB") -> str:
    try:
        value = Decimal(str(amount))
    except InvalidOperation:
        return f"{amount} {currency}".strip()
    if currency == "RUB":
        rubles = int(value) if value == value.to_integral_value() else value.normalize()
        return f"{rubles} ₽"
    return f"{value.normalize()} {currency}"


def receipt_orders_for_admin(con: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = con.execute(
        """
        SELECT so.order_uid, so.product_id, so.product_title, so.amount, so.currency,
               so.buyer_email, so.status, so.email_sent, so.paid_at, so.created_at,
               so.receipt_sent, so.receipt_sent_at, so.receipt_note,
               pe.type AS entity_type
        FROM shop_orders so
        LEFT JOIN paid_entities pe ON pe.product_id = so.product_id
        WHERE so.status = 'paid'
           OR (
                so.status <> 'canceled'
                AND so.yookassa_payment_id IS NOT NULL
                AND so.yookassa_payment_id <> ''
              )
        ORDER BY COALESCE(so.paid_at, so.created_at) DESC
        """
    ).fetchall()
    return [
        {
            **dict(row),
            "email_sent": bool(row["email_sent"]),
            "receipt_sent": bool(row["receipt_sent"]),
            "entity_type": row["entity_type"] or "product",
        }
        for row in rows
    ]


def mark_order_receipt_sent(admin: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    require_admin(admin)
    order_uid = trim_for_admin(payload.get("order_uid"), 120)
    receipt_note = str(payload.get("receipt_note") or "").strip()
    receipt_sent = 0 if payload.get("receipt_sent") is False else 1
    if not order_uid:
        raise ValueError("Не указан заказ.")
    with db() as con:
        row = con.execute("SELECT order_uid FROM shop_orders WHERE order_uid = ?", (order_uid,)).fetchone()
        if not row:
            raise LookupError("Заказ не найден.")
        if receipt_sent:
            con.execute(
                """
                UPDATE shop_orders
                SET receipt_sent = 1,
                    receipt_sent_at = ?,
                    receipt_note = COALESCE(NULLIF(?, ''), receipt_note)
                WHERE order_uid = ?
                """,
                (now_iso(), receipt_note, order_uid),
            )
        else:
            clear_note = receipt_note or "Отметка о чеке снята вручную."
            con.execute(
                """
                UPDATE shop_orders
                SET receipt_sent = 0,
                    receipt_sent_at = NULL,
                    receipt_note = ?
                WHERE order_uid = ?
                """,
                (clear_note, order_uid),
            )
        updated = con.execute(
            """
            SELECT so.order_uid, so.product_id, so.product_title, so.amount, so.currency,
                   so.buyer_email, so.status, so.email_sent, so.paid_at, so.created_at,
                   so.receipt_sent, so.receipt_sent_at, so.receipt_note,
                   pe.type AS entity_type
            FROM shop_orders so
            LEFT JOIN paid_entities pe ON pe.product_id = so.product_id
            WHERE so.order_uid = ?
            """,
            (order_uid,),
        ).fetchone()
    item = dict(updated)
    item["email_sent"] = bool(updated["email_sent"])
    item["receipt_sent"] = bool(updated["receipt_sent"])
    item["entity_type"] = updated["entity_type"] or "product"
    return {"ok": True, "order": item}


def sync_order_payment_for_admin(admin: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    require_admin(admin)
    order_uid = trim_for_admin(payload.get("order_uid"), 120)
    if not order_uid:
        raise ValueError("Не указан заказ.")
    confirm_order_return({"order_uid": order_uid})
    with db() as con:
        updated = con.execute(
            """
            SELECT so.order_uid, so.product_id, so.product_title, so.amount, so.currency,
                   so.buyer_email, so.status, so.email_sent, so.paid_at, so.created_at,
                   so.receipt_sent, so.receipt_sent_at, so.receipt_note,
                   pe.type AS entity_type
            FROM shop_orders so
            LEFT JOIN paid_entities pe ON pe.product_id = so.product_id
            WHERE so.order_uid = ?
            """,
            (order_uid,),
        ).fetchone()
    if not updated:
        raise LookupError("Заказ не найден.")
    item = dict(updated)
    item["email_sent"] = bool(updated["email_sent"])
    item["receipt_sent"] = bool(updated["receipt_sent"])
    item["entity_type"] = updated["entity_type"] or "product"
    return {"ok": True, "order": item}


def normalize_amount(value: Any) -> str:
    raw = str(value or "").strip().replace(",", ".")
    try:
        amount = Decimal(raw)
    except InvalidOperation as error:
        raise ValueError("Цена должна быть числом.") from error
    if amount < 0:
        raise ValueError("Цена не может быть отрицательной.")
    return f"{amount.quantize(Decimal('0.01'))}"


def update_paid_entity(admin: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    require_admin(admin)
    product_id = trim_for_admin(payload.get("product_id"), 80)
    title = trim_for_admin(payload.get("title"), 180)
    amount = normalize_amount(payload.get("amount")) if "amount" in payload else None
    currency = trim_for_admin(payload.get("currency") or "RUB", 12).upper()
    cover_url = str(payload.get("cover_url") or "").strip()
    delivery_url = str(payload.get("delivery_url") or "").strip()
    if not product_id:
        raise ValueError("Не указана платная сущность.")
    if not title:
        raise ValueError("Название не может быть пустым.")
    if currency != "RUB":
        raise ValueError("Сейчас поддерживается только валюта RUB.")
    with db() as con:
        row = con.execute("SELECT product_id FROM paid_entities WHERE product_id = ?", (product_id,)).fetchone()
        if not row:
            raise LookupError("Платная сущность не найдена.")
        con.execute(
            """
            UPDATE paid_entities
            SET title = ?,
                amount = COALESCE(?, amount),
                currency = ?,
                delivery_url = ?,
                cover_url = ?,
                updated_at = ?
            WHERE product_id = ?
            """,
            (title, amount, currency, delivery_url, cover_url, now_iso(), product_id),
        )
        updated = con.execute("SELECT * FROM paid_entities WHERE product_id = ?", (product_id,)).fetchone()
    return {"ok": True, "entity": paid_entity_row(updated)}


def update_paid_entity_delivery(admin: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    product_id = trim_for_admin(payload.get("product_id"), 80)
    with db() as con:
        row = con.execute("SELECT * FROM paid_entities WHERE product_id = ?", (product_id,)).fetchone()
    if not row:
        raise LookupError("Платная сущность не найдена.")
    merged = dict(row)
    merged.update(payload)
    return update_paid_entity(admin, merged)


def reset_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def send_password_reset_email(email: str, link: str) -> None:
    if not SMTP_HOST or not MAIL_FROM:
        if not production_mode():
            print(f"Password reset link for {email}: {link}")
            return
        raise RuntimeError("SMTP is not configured.")

    message = EmailMessage()
    message["Subject"] = "Восстановление пароля"
    message["From"] = MAIL_FROM
    message["To"] = email
    message.set_content(
        "Здравствуйте.\n\n"
        "Для смены пароля откройте ссылку ниже. Она действует 30 минут:\n\n"
        f"{link}\n\n"
        "Если вы не запрашивали восстановление пароля, просто игнорируйте это письмо.\n"
    )

    try:
        if SMTP_USE_SSL:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
                if SMTP_USER:
                    smtp.login(SMTP_USER, SMTP_PASSWORD)
                smtp.send_message(message)
            return

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.starttls()
            if SMTP_USER:
                smtp.login(SMTP_USER, SMTP_PASSWORD)
            smtp.send_message(message)
    except smtplib.SMTPAuthenticationError as error:
        print(f"SMTP authentication failed: code={error.smtp_code}, debug={smtp_debug_info()}")
        raise RuntimeError("SMTP: неверный логин или пароль. Проверьте SMTP_USER и SMTP_PASSWORD.") from error
    except smtplib.SMTPException as error:
        print(f"SMTP password reset send failed: {error}")
        raise RuntimeError("SMTP: не удалось отправить письмо. Проверьте настройки почты.") from error


def send_email_message(message: EmailMessage) -> None:
    if not SMTP_HOST or not MAIL_FROM:
        if not production_mode():
            print(message.as_string())
            return
        raise RuntimeError("SMTP is not configured.")

    try:
        if SMTP_USE_SSL:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as smtp:
                if SMTP_USER:
                    smtp.login(SMTP_USER, SMTP_PASSWORD)
                smtp.send_message(message)
            return

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
            smtp.starttls()
            if SMTP_USER:
                smtp.login(SMTP_USER, SMTP_PASSWORD)
            smtp.send_message(message)
    except smtplib.SMTPAuthenticationError as error:
        print(f"SMTP authentication failed: code={error.smtp_code}, debug={smtp_debug_info()}")
        raise RuntimeError("SMTP: неверный логин или пароль. Проверьте SMTP_USER и SMTP_PASSWORD.") from error
    except smtplib.SMTPException as error:
        print(f"SMTP send failed: {error}")
        raise RuntimeError("SMTP: не удалось отправить письмо. Проверьте настройки почты.") from error


def send_product_email(email: str, product: dict[str, str], product_url: str) -> None:
    message = EmailMessage()
    if product.get("kind") == "donation" or product.get("type") == "donation":
        message["Subject"] = "Спасибо за поддержку проекта"
    else:
        message["Subject"] = f"Ваш материал «{product['title']}»"
    message["From"] = MAIL_FROM
    message["To"] = email
    if product.get("kind") == "donation" or product.get("type") == "donation":
        message.set_content(
            "Здравствуйте!\n\n"
            "Спасибо за поддержку проекта «Русский язык».\n\n"
            "От меня вам небольшая благодарность ❤️\n"
            "Заберите её по ссылке:\n"
            f"{product_url}\n\n"
            "Если ссылка не открывается, скопируйте её и вставьте в адресную строку браузера.\n\n"
            "С уважением,\n"
            "Анастасия Димитриева\n"
        )
    else:
        message.set_content(
            "Здравствуйте!\n\n"
            f"Спасибо за покупку материала «{product.get('short_title') or product['title']}».\n\n"
            "Ссылка на материал:\n"
            f"{product_url}\n\n"
            "Если ссылка не открывается, скопируйте её и вставьте в адресную строку браузера.\n\n"
            "С уважением,\n"
            "Анастасия Димитриева\n"
        )
    send_email_message(message)


def send_berry_season_email(email: str, product_url: str) -> None:
    send_product_email(email, PRODUCT_BERRY_SEASON, product_url)


def send_admin_smtp_test(admin: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    require_admin(admin)
    email = normalize_email(payload.get("email"))
    validate_email(email)
    message = EmailMessage()
    message["Subject"] = "Проверка SMTP: Русский язык"
    message["From"] = MAIL_FROM
    message["To"] = email
    message.set_content(
        "Здравствуйте!\n\n"
        "Это тестовое письмо для проверки SMTP-настроек сайта.\n\n"
        "Если вы получили это письмо, отправка почты работает.\n"
    )
    send_email_message(message)
    print(f"SMTP test email sent: to={email}")
    return {
        "ok": True,
        "message": "Тестовое письмо отправлено.",
        "smtp": smtp_debug_info(),
    }


def paid_entity_row(row: sqlite3.Row) -> dict[str, str]:
    item = dict(row)
    item["id"] = item["product_id"]
    item["kind"] = item["type"]
    item["short_title"] = item["title"]
    item["is_active"] = bool(item.get("is_active"))
    return item


def product_by_slug(slug: str) -> dict[str, str]:
    clean_slug = str(slug or "").strip()
    with db() as con:
        row = con.execute("SELECT * FROM paid_entities WHERE slug = ?", (clean_slug,)).fetchone()
    if not row:
        raise ValueError("Материал не найден.")
    return paid_entity_row(row)


def product_by_id(product_id: str) -> dict[str, str] | None:
    with db() as con:
        row = con.execute("SELECT * FROM paid_entities WHERE product_id = ?", (product_id,)).fetchone()
    return paid_entity_row(row) if row else None


def product_delivery_url(product: dict[str, str]) -> str:
    delivery_url = str(product.get("delivery_url") or "").strip()
    if delivery_url:
        return delivery_url
    env_name = str(product.get("url_env") or "").strip()
    if env_name:
        env_url = os.getenv(env_name, "").strip()
        if env_url:
            return env_url
    if product.get("id") == PRODUCT_BERRY_SEASON["id"] or product.get("product_id") == PRODUCT_BERRY_SEASON["id"]:
        return os.getenv("BERRY_SEASON_PRODUCT_URL", "").strip()
    return ""


def game_entry_file(slug: str, relative_path: str) -> str:
    clean_path = relative_path or "index.html"
    if clean_path in {"", "index.html"} and slug == "grammar-zoo":
        return "grammar_zoo_engine.html"
    return clean_path


def teacher_games(user: dict[str, Any]) -> dict[str, Any]:
    require_teacher(user)
    teacher_email = normalize_email(user.get("email") or user.get("username"))
    with db() as con:
        purchased_rows = con.execute(
            """
            SELECT pe.slug, pe.product_id, pe.title, pe.delivery_url, pe.url_env,
                   so.order_uid, so.paid_at, so.created_at
            FROM shop_orders so
            JOIN paid_entities pe ON pe.product_id = so.product_id
            WHERE so.status = 'paid'
              AND pe.type = 'product'
              AND LOWER(so.buyer_email) = ?
            ORDER BY COALESCE(so.paid_at, so.created_at) DESC
            """,
            (teacher_email,),
        ).fetchall()
        created_rows = con.execute(
            """
            SELECT public_id, title, description, mechanic, created_at, updated_at,
                   is_active, is_deleted, use_count
            FROM game_sets
            WHERE teacher_id = ? AND is_deleted = 0
            ORDER BY created_at DESC
            """,
            (user["user_id"],),
        ).fetchall()

    purchased = []
    seen_products: set[str] = set()
    for row in purchased_rows:
        if row["product_id"] in seen_products:
            continue
        seen_products.add(row["product_id"])
        product = {
            "id": row["product_id"],
            "product_id": row["product_id"],
            "slug": row["slug"],
            "title": row["title"],
            "delivery_url": row["delivery_url"],
            "url_env": row["url_env"],
        }
        url = product_delivery_url(product)
        if not url and row["slug"] in HTML_GAMES:
            url = f"{APP_BASE_URL}/full-games/{row['slug']}/{game_entry_file(row['slug'], 'index.html')}"
        purchased.append(
            {
                "kind": "purchased",
                "slug": row["slug"],
                "title": row["title"],
                "url": url,
                "order_uid": row["order_uid"],
                "paid_at": row["paid_at"],
                "created_at": row["created_at"],
            }
        )

    created = [
        {
            "kind": "created",
            "public_id": row["public_id"],
            "title": row["title"],
            "description": row["description"],
            "mechanic": row["mechanic"],
            "url": public_game_url(row["mechanic"], row["public_id"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "is_active": bool(row["is_active"]),
            "use_count": int(row["use_count"] or 0),
        }
        for row in created_rows
    ]
    return {"purchased": purchased, "created": created}


def yookassa_env(product: dict[str, str] | None = None) -> tuple[str, str, str]:
    shop_id = os.getenv("YOOKASSA_SHOP_ID", "").strip()
    secret_key = os.getenv("YOOKASSA_SECRET_KEY", "").strip()
    product_url = product_delivery_url(product or PRODUCT_BERRY_SEASON)
    if not shop_id or not secret_key:
        print(
            "YooKassa env missing: "
            f"YOOKASSA_SHOP_ID={'yes' if shop_id else 'no'}, "
            f"YOOKASSA_SECRET_KEY={'yes' if secret_key else 'no'}"
        )
        raise RuntimeError("Оплата временно недоступна. Попробуйте позже")
    if not product_url:
        env_name = (product or PRODUCT_BERRY_SEASON)["url_env"]
        print(f"YooKassa env missing: {env_name}=no")
        raise RuntimeError("Материал временно недоступен. Попробуйте позже")
    return shop_id, secret_key, product_url


def yookassa_api_request(shop_id: str, secret_key: str, path: str, payload: dict[str, Any] | None = None, idempotence_key: str = "") -> dict[str, Any]:
    auth = base64.b64encode(f"{shop_id}:{secret_key}".encode("utf-8")).decode("ascii")
    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json",
    }
    data = None
    method = "GET"
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        method = "POST"
        if idempotence_key:
            headers["Idempotence-Key"] = idempotence_key
    request = Request(
        f"https://api.yookassa.ru/v3{path}",
        data=data,
        headers=headers,
        method=method,
    )
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def create_yookassa_payment(shop_id: str, secret_key: str, product: dict[str, str], order_uid: str, email: str) -> dict[str, Any]:
    payload = {
        "amount": {
            "value": product["amount"],
            "currency": product["currency"],
        },
        "capture": True,
        "confirmation": {
            "type": "redirect",
            "return_url": f"https://dimitrieva-av.ru/shop/thanks?order={order_uid}",
        },
        "description": product["title"],
        "metadata": {
            "product_id": product["id"],
            "order_uid": order_uid,
            "email": email,
            "type": product["kind"],
        },
    }
    try:
        return yookassa_api_request(shop_id, secret_key, "/payments", payload, order_uid)
    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        print(f"YooKassa payment error: {error.code} {details}")
        raise RuntimeError("Не удалось создать платёж. Попробуйте позже.") from error
    except URLError as error:
        print(f"YooKassa connection error: {error}")
        raise RuntimeError("Не удалось создать платёж. Попробуйте позже.") from error


def get_yookassa_payment(shop_id: str, secret_key: str, payment_id: str) -> dict[str, Any]:
    try:
        return yookassa_api_request(shop_id, secret_key, f"/payments/{payment_id}")
    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        print(f"YooKassa payment status error: {error.code} {details}")
        raise RuntimeError("Не удалось проверить платёж. Попробуйте позже.") from error
    except URLError as error:
        print(f"YooKassa payment status connection error: {error}")
        raise RuntimeError("Не удалось проверить платёж. Попробуйте позже.") from error


def create_product_payment(payload: dict[str, Any], default_slug: str = "fruit-garden-ik-ek") -> dict[str, Any]:
    email = normalize_email(payload.get("email"))
    validate_email(email)
    product = product_by_slug(str(payload.get("product") or default_slug))
    if product["id"] == "verb_conjugation_quest" and datetime.now().date() <= date(2026, 7, 3):
        raise RuntimeError("До конца 03.07.2026 игра доступна бесплатно в канале MAX.")
    if not product.get("is_active", True):
        raise RuntimeError("Материал временно недоступен. Попробуйте позже.")
    shop_id, secret_key, _product_url = yookassa_env(product)
    order_uid = secrets.token_urlsafe(18)
    with db() as con:
        con.execute(
            """
            INSERT INTO shop_orders (
                order_uid, product_id, product_title, amount, currency,
                buyer_email, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
            """,
            (
                order_uid,
                product["id"],
                product["title"],
                product["amount"],
                product["currency"],
                email,
                now_iso(),
            ),
        )
    try:
        payment = create_yookassa_payment(shop_id, secret_key, product, order_uid, email)
    except RuntimeError:
        with db() as con:
            con.execute("UPDATE shop_orders SET status = 'payment_error' WHERE order_uid = ?", (order_uid,))
        raise
    payment_id = str(payment.get("id") or "")
    confirmation_url = (payment.get("confirmation") or {}).get("confirmation_url")
    if not payment_id or not confirmation_url:
        with db() as con:
            con.execute("UPDATE shop_orders SET status = 'payment_error' WHERE order_uid = ?", (order_uid,))
        raise RuntimeError("Не удалось создать платёж. Попробуйте позже.")
    with db() as con:
        con.execute(
            "UPDATE shop_orders SET yookassa_payment_id = ? WHERE order_uid = ?",
            (payment_id, order_uid),
        )
    return {"confirmation_url": confirmation_url}


def create_berry_season_payment(payload: dict[str, Any]) -> dict[str, Any]:
    return create_product_payment(payload, "fruit-garden-ik-ek")


def deliver_product_order(order_uid: str, payment_id: str, raw_payload: str = "") -> dict[str, Any]:
    with db() as con:
        order = con.execute("SELECT * FROM shop_orders WHERE order_uid = ?", (order_uid,)).fetchone()
    if not order:
        raise ValueError("Заказ не найден.")
    product = product_by_id(str(order["product_id"] or ""))
    if not product:
        raise ValueError("Материал не найден.")

    shop_id, secret_key, product_url = yookassa_env(product)
    payment = get_yookassa_payment(shop_id, secret_key, payment_id)
    payment_status = str(payment.get("status") or "")
    metadata = payment.get("metadata") if isinstance(payment.get("metadata"), dict) else {}
    if str(metadata.get("order_uid") or "") != order_uid:
        raise ValueError("Платёж не найден.")

    with db() as con:
        order = con.execute("SELECT * FROM shop_orders WHERE order_uid = ?", (order_uid,)).fetchone()
        if not order or order["product_id"] != product["id"]:
            raise ValueError("Заказ не найден.")
        if payment_status == "canceled":
            con.execute(
                "UPDATE shop_orders SET status = 'canceled', raw_webhook = COALESCE(?, raw_webhook) WHERE order_uid = ?",
                (raw_payload or None, order_uid),
            )
            return {"ok": True, "status": "canceled", "email_sent": bool(order["email_sent"])}
        if payment_status != "succeeded":
            return {"ok": True, "status": payment_status or order["status"], "email_sent": bool(order["email_sent"])}
        con.execute(
            """
            UPDATE shop_orders
            SET status = 'paid',
                paid_at = COALESCE(paid_at, ?),
                raw_webhook = COALESCE(?, raw_webhook)
            WHERE order_uid = ?
            """,
            (now_iso(), raw_payload or None, order_uid),
        )
        if int(order["email_sent"] or 0):
            return {"ok": True, "status": "paid", "email_sent": True}
        buyer_email = order["buyer_email"]

    send_product_email(buyer_email, product, product_url)
    with db() as con:
        con.execute("UPDATE shop_orders SET email_sent = 1 WHERE order_uid = ?", (order_uid,))
    print(f"Product email sent: order_uid={order_uid}, product_id={product['id']}")
    return {"ok": True, "status": "paid", "email_sent": True}


def deliver_berry_season_order(order_uid: str, payment_id: str, raw_payload: str = "") -> dict[str, Any]:
    return deliver_product_order(order_uid, payment_id, raw_payload)


def confirm_order_return(payload: dict[str, Any]) -> dict[str, Any]:
    order_uid = str(payload.get("order_uid") or "").strip()
    if not order_uid:
        raise ValueError("Заказ не найден.")
    with db() as con:
        order = con.execute(
            """
            SELECT order_uid, yookassa_payment_id, status, email_sent
            FROM shop_orders
            WHERE order_uid = ?
            """,
            (order_uid,),
        ).fetchone()
    if not order:
        raise ValueError("Заказ не найден.")
    if int(order["email_sent"] or 0):
        return {"ok": True, "status": order["status"], "email_sent": True}
    payment_id = str(order["yookassa_payment_id"] or "")
    if not payment_id:
        return {"ok": True, "status": order["status"], "email_sent": False}
    return deliver_product_order(order_uid, payment_id)


def confirm_berry_season_return(payload: dict[str, Any]) -> dict[str, Any]:
    return confirm_order_return(payload)


def resend_order_by_email(payload: dict[str, Any], default_slug: str | None = None) -> dict[str, Any]:
    email = normalize_email(payload.get("email"))
    validate_email(email)
    requested_product = str(payload.get("product") or "").strip()
    product = product_by_slug(requested_product or default_slug) if (requested_product or default_slug) else None
    with db() as con:
        if product:
            order = con.execute(
                """
                SELECT order_uid, yookassa_payment_id, status, email_sent
                FROM shop_orders
                WHERE LOWER(buyer_email) = ?
                  AND product_id = ?
                  AND yookassa_payment_id IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (email, product["id"]),
            ).fetchone()
        else:
            order = con.execute(
                """
                SELECT order_uid, yookassa_payment_id, status, email_sent
                FROM shop_orders
                WHERE LOWER(buyer_email) = ?
                  AND yookassa_payment_id IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (email,),
            ).fetchone()
    if not order:
        raise ValueError("Заказ с этой почтой не найден.")
    if int(order["email_sent"] or 0):
        return {"ok": True, "status": order["status"], "email_sent": True}
    return deliver_product_order(order["order_uid"], order["yookassa_payment_id"])


def resend_berry_season_by_email(payload: dict[str, Any]) -> dict[str, Any]:
    return resend_order_by_email(payload, "fruit-garden-ik-ek")


def process_yookassa_webhook(payload: dict[str, Any], raw_payload: str) -> dict[str, Any]:
    event = str(payload.get("event") or "")
    payment = payload.get("object") if isinstance(payload.get("object"), dict) else {}
    payment_id = str(payment.get("id") or "")
    metadata = payment.get("metadata") if isinstance(payment.get("metadata"), dict) else {}
    order_uid = str(metadata.get("order_uid") or "")
    product_id = str(metadata.get("product_id") or "")
    print(f"YooKassa webhook received: event={event}, order_uid={order_uid or '-'}, payment_id={payment_id or '-'}")
    if not payment_id or not order_uid:
        return {"ok": True}

    should_send_email = False
    buyer_email = ""
    with db() as con:
        order = con.execute("SELECT * FROM shop_orders WHERE order_uid = ?", (order_uid,)).fetchone()
        if not order:
            print(f"YooKassa webhook ignored: order not found, order_uid={order_uid}")
            return {"ok": True}
        product = product_by_id(str(order["product_id"] or ""))
        if not product or product_id != product["id"]:
            print(f"YooKassa webhook ignored: product mismatch, order_uid={order_uid}")
            return {"ok": True}

        if event == "payment.succeeded":
            con.execute(
                """
                UPDATE shop_orders
                SET status = 'paid',
                    paid_at = COALESCE(paid_at, ?),
                    yookassa_payment_id = COALESCE(yookassa_payment_id, ?),
                    raw_webhook = ?
                WHERE order_uid = ?
                """,
                (now_iso(), payment_id, raw_payload, order_uid),
            )
            if not int(order["email_sent"] or 0):
                should_send_email = True
                buyer_email = order["buyer_email"]
        elif event == "payment.canceled":
            con.execute(
                """
                UPDATE shop_orders
                SET status = 'canceled',
                    yookassa_payment_id = COALESCE(yookassa_payment_id, ?),
                    raw_webhook = ?
                WHERE order_uid = ?
                """,
                (payment_id, raw_payload, order_uid),
            )
    if should_send_email:
        product = product_by_id(product_id)
        product_url = product_delivery_url(product) if product else ""
        if not product_url:
            raise RuntimeError("Материал временно недоступен. Попробуйте позже")
        send_product_email(buyer_email, product, product_url)
        with db() as con:
            con.execute("UPDATE shop_orders SET email_sent = 1 WHERE order_uid = ?", (order_uid,))
        print(f"Product email sent by webhook: order_uid={order_uid}, product_id={product_id}")
    return {"ok": True}


def request_password_reset(payload: dict[str, Any]) -> dict[str, Any]:
    email = normalize_email(payload.get("email") or payload.get("username"))
    neutral = {
        "ok": True,
        "message": "Если такой email есть в системе, мы отправили ссылку для восстановления пароля.",
    }
    if not email:
        return neutral

    with db() as con:
        row = con.execute(
            """
            SELECT user_id, username, COALESCE(email, username) AS email
            FROM users
            WHERE LOWER(COALESCE(email, '')) = ?
               OR (email IS NULL AND LOWER(username) = ? AND instr(username, '@') > 1)
            """,
            (email, email),
        ).fetchone()
        if not row:
            return neutral
        token = secrets.token_urlsafe(32)
        expires_at = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat(timespec="seconds")
        con.execute(
            """
            INSERT INTO password_reset_tokens
                (token_id, user_id, token_hash, expires_at, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (secrets.token_hex(12), row["user_id"], reset_token_hash(token), expires_at, now_iso()),
        )
    send_password_reset_email(row["email"], f"{APP_BASE_URL}/reset-password?token={token}")
    return neutral


def reset_password_by_token(payload: dict[str, Any]) -> dict[str, Any]:
    token = str(payload.get("token") or "").strip()
    new_password = str(payload.get("password") or payload.get("new_password") or "")
    if not token or len(new_password) < 6:
        raise ValueError("Укажите токен и новый пароль не короче 6 символов.")
    token_hash = reset_token_hash(token)
    with db() as con:
        row = con.execute(
            """
            SELECT prt.*, u.username
            FROM password_reset_tokens prt
            JOIN users u ON u.user_id = prt.user_id
            WHERE prt.token_hash = ? AND prt.used_at IS NULL
            """,
            (token_hash,),
        ).fetchone()
        if not row:
            raise ValueError("Ссылка восстановления недействительна.")
        expires_at = datetime.fromisoformat(row["expires_at"])
        if expires_at < datetime.now(timezone.utc):
            raise ValueError("Срок действия ссылки истек.")
        salt = secrets.token_hex(16)
        con.execute(
            """
            UPDATE users
            SET password_salt = ?,
                password_hash = ?,
                password_reset_required = 0
            WHERE user_id = ?
            """,
            (salt, password_hash(new_password, salt), row["user_id"]),
        )
        con.execute(
            "UPDATE password_reset_tokens SET used_at = ? WHERE token_id = ?",
            (now_iso(), row["token_id"]),
        )
    return {"ok": True, "username": row["username"]}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def guess_type(self, path: str) -> str:
        content_type = super().guess_type(path)
        if content_type in {"text/html", "text/css", "text/javascript", "application/javascript"}:
            return f"{content_type}; charset=utf-8"
        return content_type

    def send_json(self, data: Any, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_download(self, body: bytes, filename: str, content_type: str) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_html_game_file(self, slug: str, relative_path: str) -> None:
        game_dir = HTML_GAMES.get(slug)
        if not game_dir:
            self.send_json({"error": "Game not found"}, HTTPStatus.NOT_FOUND)
            return
        relative_path = game_entry_file(slug, unquote(relative_path).lstrip("/") or "index.html")
        file_path = (game_dir / relative_path).resolve()
        game_root = game_dir.resolve()
        try:
            file_path.relative_to(game_root)
        except ValueError:
            self.send_json({"error": "Game file not found"}, HTTPStatus.NOT_FOUND)
            return
        if not file_path.is_file():
            self.send_json({"error": "Game file not found"}, HTTPStatus.NOT_FOUND)
            return
        if relative_path in {"index.html", ""}:
            record_public_game_visit(slug, None, self.path)
        body = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", self.guess_type(str(file_path)))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_public_game_file(self, slug: str, relative_path: str) -> None:
        game_dir = PUBLIC_GAMES.get(slug)
        if not game_dir:
            self.send_json({"error": "Game not found"}, HTTPStatus.NOT_FOUND)
            return
        relative_path = game_entry_file(slug, unquote(relative_path).lstrip("/") or "index.html")
        file_path = (game_dir / relative_path).resolve()
        game_root = game_dir.resolve()
        try:
            file_path.relative_to(game_root)
        except ValueError:
            self.send_json({"error": "Game file not found"}, HTTPStatus.NOT_FOUND)
            return
        if not file_path.is_file():
            self.send_json({"error": "Game file not found"}, HTTPStatus.NOT_FOUND)
            return
        if relative_path in {"index.html", ""}:
            query = parse_qs(urlparse(self.path).query)
            record_public_game_visit(slug, (query.get("set") or [None])[0], self.path)
        body = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", self.guess_type(str(file_path)))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_full_game_file(self, slug: str, relative_path: str) -> None:
        game_dir = HTML_GAMES.get(slug)
        if not game_dir:
            self.send_json({"error": "Game not found"}, HTTPStatus.NOT_FOUND)
            return
        relative_path = game_entry_file(slug, unquote(relative_path).lstrip("/") or "index.html")
        file_path = (game_dir / relative_path).resolve()
        game_root = game_dir.resolve()
        try:
            file_path.relative_to(game_root)
        except ValueError:
            self.send_json({"error": "Game file not found"}, HTTPStatus.NOT_FOUND)
            return
        if not file_path.is_file():
            self.send_json({"error": "Game file not found"}, HTTPStatus.NOT_FOUND)
            return
        body = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", self.guess_type(str(file_path)))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def current_user(self) -> dict[str, Any] | None:
        header = self.headers.get("Authorization", "")
        token = header.removeprefix("Bearer ").strip()
        session = SESSIONS.get(token)
        if session:
            session["last_seen_at"] = now_iso()
        return session["user"] if session else None

    def require_user(self) -> dict[str, Any]:
        user = self.current_user()
        if not user:
            raise PermissionError("Нужен вход в приложение.")
        return user

    def request_ip(self) -> str:
        forwarded = self.headers.get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",", 1)[0].strip()
        return self.client_address[0] if self.client_address else ""

    def request_user_agent(self) -> str:
        return self.headers.get("User-Agent", "")

    def require_user_with_consents(self) -> dict[str, Any]:
        user = self.require_user()
        if not user_has_required_consents(user["user_id"]):
            raise PermissionError("Перед началом работы необходимо принять документы по обработке персональных данных.")
        return user

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/bootstrap":
                self.send_json(activity_bootstrap("ege9", self.current_user()))
            elif parsed.path == "/api/documents/privacy":
                self.send_json(active_document("privacy_policy"))
            elif parsed.path == "/api/documents/consent":
                self.send_json(active_document("personal_data_consent"))
            elif parsed.path == "/api/documents/terms":
                self.send_json(active_document("terms"))
            elif parsed.path.startswith("/api/public-documents/"):
                slug = parsed.path.rsplit("/", 1)[-1]
                self.send_json(public_text_document(slug))
            elif parsed.path == "/api/activities":
                self.require_user_with_consents()
                self.send_json({"activities": ACTIVITIES})
            elif parsed.path.startswith("/api/apps/") and parsed.path.endswith("/bootstrap"):
                parts = parsed.path.strip("/").split("/")
                user = self.require_user_with_consents()
                self.send_json(activity_bootstrap(parts[2], user))
            elif parsed.path in {"/api/me", "/api/auth/me"}:
                self.send_json({"user": self.current_user()})
            elif parsed.path == "/api/me/consents":
                user = self.require_user()
                self.send_json(consent_status(user["user_id"]))
            elif parsed.path == "/api/progress":
                self.send_json(progress_for(self.require_user_with_consents()))
            elif parsed.path == "/api/progress/export":
                query = parse_qs(parsed.query)
                body, filename, content_type = progress_export(self.require_user(), query.get("section", ["recent"])[0])
                self.send_download(body, filename, content_type)
            elif parsed.path == "/api/shop/products":
                self.send_json(shop_products_public())
            elif parsed.path == "/api/games/sources":
                require_teacher_or_admin(self.require_user_with_consents())
                self.send_json(game_sources_for_teacher())
            elif parsed.path == "/api/teacher/games":
                self.send_json(teacher_games(self.require_user_with_consents()))
            elif parsed.path.startswith("/api/games/sets/"):
                public_id = parsed.path.rsplit("/", 1)[-1]
                self.send_json(public_game_set(public_id))
            elif parsed.path == "/api/admin":
                self.send_json(admin_overview(self.require_user()))
            elif parsed.path == "/html-games/":
                self.path = "/index.html"
                super().do_GET()
            elif parsed.path.startswith("/html-games/"):
                parts = parsed.path.strip("/").split("/", 2)
                if len(parts) < 2:
                    self.send_json({"error": "Game not found"}, HTTPStatus.NOT_FOUND)
                    return
                self.send_html_game_file(parts[1], parts[2] if len(parts) > 2 else "index.html")
            elif parsed.path == "/games/":
                self.path = "/index.html"
                super().do_GET()
            elif parsed.path.startswith("/games/"):
                parts = parsed.path.strip("/").split("/", 2)
                if len(parts) < 2:
                    self.send_json({"error": "Game not found"}, HTTPStatus.NOT_FOUND)
                    return
                self.send_public_game_file(parts[1], parts[2] if len(parts) > 2 else "index.html")
            elif parsed.path == "/full-games/":
                self.path = "/index.html"
                super().do_GET()
            elif parsed.path.startswith("/full-games/"):
                parts = parsed.path.strip("/").split("/", 2)
                if len(parts) < 2:
                    self.send_json({"error": "Game not found"}, HTTPStatus.NOT_FOUND)
                    return
                self.send_full_game_file(parts[1], parts[2] if len(parts) > 2 else "index.html")
            elif parsed.path.startswith("/images/"):
                image_name = Path(parsed.path).name
                image_path = (IMAGES_DIR / image_name).resolve()
                if not str(image_path).startswith(str(IMAGES_DIR.resolve())) or not image_path.exists():
                    self.send_json({"error": "Image not found"}, HTTPStatus.NOT_FOUND)
                    return
                body = image_path.read_bytes()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", mimetypes.guess_type(image_path.name)[0] or "application/octet-stream")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                if (
                    parsed.path == "/"
                    or parsed.path == "/apps"
                    or parsed.path.startswith("/apps/")
                    or parsed.path in {
                        "/login",
                        "/register",
                        "/forgot-password",
                        "/reset-password",
                        "/privacy",
                        "/consent",
                        "/terms",
                        "/contacts",
                        "/delivery",
                        "/refund",
                        "/offer",
                        "/admin",
                        "/teacher",
                        "/student",
                        "/games",
                        "/donate",
                        "/shop",
                        "/support",
                    }
                    or parsed.path.startswith("/shop/")
                ):
                    self.path = "/index.html"
                super().do_GET()
        except PermissionError as error:
            self.send_json({"error": str(error)}, HTTPStatus.UNAUTHORIZED)
        except LookupError as error:
            self.send_json({"error": str(error)}, HTTPStatus.NOT_FOUND)
        except Exception as error:
            self.send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/yookassa/webhook":
                length = int(self.headers.get("Content-Length") or 0)
                raw_payload = self.rfile.read(length).decode("utf-8") if length else "{}"
                payload = json.loads(raw_payload or "{}")
            else:
                raw_payload = ""
                payload = parse_json_body(self)
            if parsed.path in {"/api/login", "/api/auth/login"}:
                username = normalize_email(payload.get("email") or payload.get("username"))
                password = str(payload.get("password") or "")
                with db() as con:
                    row = con.execute(
                        """
                        SELECT * FROM users
                        WHERE LOWER(COALESCE(email, '')) = ?
                           OR (email IS NULL AND LOWER(username) = ?)
                        """,
                        (username, username),
                    ).fetchone()
                    if row and int(row["password_reset_required"] or 0):
                        self.send_json({"error": "Пароль сброшен администратором. Зарегистрируйтесь с тем же логином и кодом учителя, чтобы задать новый пароль."}, HTTPStatus.UNAUTHORIZED)
                        return
                    if not row or not verify_password(password, row["password_salt"], row["password_hash"]):
                        self.send_json({"error": "Неверный логин или пароль."}, HTTPStatus.UNAUTHORIZED)
                        return
                    if needs_password_rehash(row["password_hash"]):
                        salt = secrets.token_hex(16)
                        con.execute(
                            """
                            UPDATE users
                            SET password_salt = ?, password_hash = ?
                            WHERE user_id = ?
                            """,
                            (salt, password_hash(password, salt), row["user_id"]),
                        )
                        row = con.execute("SELECT * FROM users WHERE user_id = ?", (row["user_id"],)).fetchone()
                token = secrets.token_urlsafe(24)
                user = public_user(row)
                SESSIONS[token] = {"user": user, "created_at": now_iso()}
                self.send_json({"token": token, "user": user})
            elif parsed.path in {"/api/register", "/api/auth/register"}:
                user = register_user(payload, self.request_ip(), self.request_user_agent())
                token = secrets.token_urlsafe(24)
                SESSIONS[token] = {"user": user, "created_at": now_iso()}
                self.send_json({"token": token, "user": user})
            elif parsed.path == "/api/heartbeat":
                self.send_json(record_visitor_heartbeat(self.current_user(), payload, self.request_ip(), self.request_user_agent()))
            elif parsed.path in {"/api/logout", "/api/auth/logout"}:
                header = self.headers.get("Authorization", "")
                token = header.removeprefix("Bearer ").strip()
                SESSIONS.pop(token, None)
                self.send_json({"ok": True})
            elif parsed.path in {"/api/forgot-password", "/api/auth/forgot-password"}:
                self.send_json(request_password_reset(payload))
            elif parsed.path in {"/api/reset-password", "/api/auth/reset-password"}:
                self.send_json(reset_password_by_token(payload))
            elif parsed.path == "/api/me/consents":
                user = self.require_user()
                status = record_user_consent(user["user_id"], self.request_ip(), self.request_user_agent())
                user = {**user, "has_required_consents": status["has_required_consents"]}
                header = self.headers.get("Authorization", "")
                token = header.removeprefix("Bearer ").strip()
                if token in SESSIONS:
                    SESSIONS[token]["user"] = user
                self.send_json(status)
            elif parsed.path == "/api/practice/start":
                self.send_json(start_practice(self.require_user_with_consents(), payload))
            elif parsed.path == "/api/practice/submit":
                self.send_json(submit_practice(self.require_user_with_consents(), payload))
            elif parsed.path == "/api/practice/check":
                self.send_json(check_practice_answer(self.require_user_with_consents(), payload))
            elif parsed.path.startswith("/api/apps/") and "/practice/" in parsed.path:
                parts = parsed.path.strip("/").split("/")
                self.send_json(activity_post(parts[2], parts[-1], self.require_user_with_consents(), payload))
            elif parsed.path == "/api/teacher/test":
                body, filename, content_type = build_test_file(self.require_user(), payload)
                self.send_download(body, filename, content_type)
            elif parsed.path == "/api/games/sets/from-base":
                self.send_json(create_game_set_from_base(self.require_user_with_consents(), payload))
            elif parsed.path == "/api/games/sets/upload-json":
                self.send_json(create_game_set_from_upload(self.require_user_with_consents(), payload))
            elif parsed.path == "/api/shop/create-payment":
                try:
                    self.send_json(create_product_payment(payload))
                except RuntimeError as error:
                    self.send_json({"error": str(error)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            elif parsed.path == "/api/shop/confirm-return":
                try:
                    self.send_json(confirm_order_return(payload))
                except RuntimeError as error:
                    self.send_json({"error": str(error)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            elif parsed.path == "/api/shop/resend-by-email":
                try:
                    self.send_json(resend_order_by_email(payload))
                except RuntimeError as error:
                    self.send_json({"error": str(error)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            elif parsed.path == "/api/shop/berry-season/create-payment":
                try:
                    self.send_json(create_berry_season_payment(payload))
                except RuntimeError as error:
                    self.send_json({"error": str(error)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            elif parsed.path == "/api/shop/berry-season/confirm-return":
                try:
                    self.send_json(confirm_berry_season_return(payload))
                except RuntimeError as error:
                    self.send_json({"error": str(error)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            elif parsed.path == "/api/shop/berry-season/resend-by-email":
                try:
                    self.send_json(resend_berry_season_by_email(payload))
                except RuntimeError as error:
                    self.send_json({"error": str(error)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            elif parsed.path == "/api/yookassa/webhook":
                self.send_json(process_yookassa_webhook(payload, raw_payload))
            elif parsed.path == "/api/admin/test-email":
                try:
                    self.send_json(send_admin_smtp_test(self.require_user(), payload))
                except RuntimeError as error:
                    self.send_json({"error": str(error), "smtp": smtp_debug_info()}, HTTPStatus.INTERNAL_SERVER_ERROR)
            elif parsed.path == "/api/admin/reset-password":
                self.send_json(reset_user_password(self.require_user(), payload))
            elif parsed.path == "/api/admin/users/delete":
                self.send_json(delete_user_for_admin(self.require_user(), payload))
            elif parsed.path == "/api/admin/users/delete-suspicious":
                self.send_json(delete_suspicious_users_for_admin(self.require_user(), payload))
            elif parsed.path == "/api/admin/delivery-url":
                self.send_json(update_paid_entity_delivery(self.require_user(), payload))
            elif parsed.path == "/api/admin/paid-entity":
                self.send_json(update_paid_entity(self.require_user(), payload))
            elif parsed.path == "/api/admin/orders/mark-receipt-sent":
                self.send_json(mark_order_receipt_sent(self.require_user(), payload))
            elif parsed.path == "/api/admin/orders/sync-payment":
                self.send_json(sync_order_payment_for_admin(self.require_user(), payload))
            elif parsed.path == "/api/admin/games/toggle":
                self.send_json(toggle_admin_game(self.require_user(), payload))
            elif parsed.path in {"/api/admin/games/delete", "/api/games/sets/delete"}:
                self.send_json(soft_delete_game(self.require_user(), payload))
            else:
                self.send_json({"error": "Unknown endpoint"}, HTTPStatus.NOT_FOUND)
        except PermissionError as error:
            self.send_json({"error": str(error)}, HTTPStatus.UNAUTHORIZED)
        except Exception as error:
            self.send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)


def main() -> int:
    configure_console()
    ensure_app_db()
    host = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("HOST", DEFAULT_HOST)
    port = int(sys.argv[2]) if len(sys.argv) > 2 else int(os.environ.get("PORT", DEFAULT_PORT))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"EGE Russian app: http://{host}:{port}")
    print(f"Words loaded: {len(WORDS)}; rules: {len(RULES)}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
