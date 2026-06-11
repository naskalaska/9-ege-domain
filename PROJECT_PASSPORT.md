# Паспорт проекта

Обновлено: 11 июня 2026.

## 1. Назначение проекта

Проект - единая образовательная платформа по русскому языку. Внутри одного сайта собраны:

- тренажеры ЕГЭ по заданиям 9, 10 и 11;
- личные кабинеты ученика, учителя и администратора;
- учет прогресса, ошибок и повторений;
- публичные страницы сайта;
- каталог HTML-игр;
- магазин цифровых материалов с оплатой через ЮKassa для одного подключенного продукта.

Основной домен в настройках: `https://dimitrieva-av.ru`.

## 2. Технологии

- Backend: Python, стандартная библиотека, `http.server.ThreadingHTTPServer`.
- Frontend: обычные HTML, CSS и JavaScript без сборщика.
- База данных: SQLite.
- Деплой: Docker, Docker Compose, Render/Portainer.
- Внешние сервисы:
  - SMTP для писем восстановления пароля, тестовых писем и доставки материала после оплаты;
  - ЮKassa для оплаты продукта `berry_season`.

`requirements.txt` сейчас не содержит внешних зависимостей: приложение рассчитано на стандартную библиотеку Python.

## 3. Главные точки входа

- `app/server.py` - основной сервер проекта. В нем находятся маршруты, авторизация, работа с базой, логика ЕГЭ-9, подключение модулей ЕГЭ-10 и ЕГЭ-11, магазин, игры, документы и админка.
- `app/static/index.html` - HTML-каркас приложения с шаблонами входа и рабочего кабинета.
- `app/static/app.js` - основной фронтенд: роутинг на клиенте, личные кабинеты, тренажеры, публичные страницы, магазин, формы оплаты, админка.
- `app/static/styles.css` - все стили основного сайта.
- `data/ege_app.db` - локальная SQLite-база данных.
- `docker-compose.yml` - запуск контейнера с volume `ege_platform_data`.
- `Dockerfile` - сборка приложения.

## 4. Структура проекта

```text
.
├── app/
│   ├── server.py
│   ├── ege10_module.py
│   ├── ege11_module.py
│   ├── static/
│   │   ├── index.html
│   │   ├── app.js
│   │   ├── styles.css
│   │   ├── favicon.ico
│   │   ├── logo.jpg
│   │   └── assets/
│   │       ├── landing/
│   │       └── shop/
│   ├── HTML/
│   │   ├── berry-season-ik-ek/
│   │   ├── homogeneous-members-magic/
│   │   ├── suffixes-nouns/
│   │   └── русскоязычные исходные папки игр
│   ├── docs/
│   │   ├── contacts.txt
│   │   ├── delivery.txt
│   │   ├── refund.txt
│   │   ├── offer.txt
│   │   ├── support_stub.txt
│   │   └── common_requirements.txt
│   └── SHOP/
├── data/
│   ├── ege_app.db
│   └── *.log
├── images/
├── ege9_final_grouped_by_orthogram_v4.json
├── ege10_words_by_orthogram.json
├── ege11_suffix_words_v4.json
├── .env.example
├── docker-compose.yml
├── Dockerfile
└── README.md
```

Резервные папки:

- `app Backup1.0/` - старая копия приложения;
- `Backup streamlit/` - старая Streamlit-версия.

## 5. Учебные базы

| Модуль | Файл | Категорий | Подправил | Слов |
|---|---|---:|---:|---:|
| ЕГЭ-9 | `ege9_final_grouped_by_orthogram_v4.json` | 6 | 51 | 911 |
| ЕГЭ-10 | `ege10_words_by_orthogram.json` | 5 | 9 | 944 |
| ЕГЭ-11 | `ege11_suffix_words_v4.json` | 5 | 25 | 627 |

Загрузка баз:

- ЕГЭ-9 загружается прямо в `app/server.py` через `load_words()`;
- ЕГЭ-10 загружается в `app/ege10_module.py`;
- ЕГЭ-11 загружается в `app/ege11_module.py`;
- главный сервер импортирует модули 10 и 11 и использует их для bootstrap и practice API.

## 6. Роли пользователей

Поддерживаются роли:

- `admin` - видит административный обзор, пользователей, недавние попытки, созданные игры, посещения игр, может сбрасывать пароли и тестировать SMTP;
- `teacher` - видит учеников, статистику, код учителя, может собирать тесты и создавать HTML-игры из своих баз;
- `student` - проходит тренировки, видит свой прогресс и копилку ошибок.

Ученики могут привязываться к учителю по коду. Если ученик регистрируется без кода, фронтенд предлагает подтверждение, после чего используется fallback-код `T-DDC378`.

## 7. Авторизация и персональные данные

Реализовано:

- регистрация ученика и учителя;
- вход и выход;
- токены сессий в памяти процесса;
- хранение токена на фронтенде в `localStorage` под ключом `ege_token`;
- PBKDF2-SHA256 для новых паролей;
- поддержка старых SHA-256-хешей с обновлением после успешного входа;
- восстановление пароля через email;
- обязательное принятие документов по персональным данным;
- публичные страницы документов `/privacy`, `/consent`, `/terms`.

Версии документов задаются переменными:

- `PRIVACY_POLICY_VERSION`;
- `CONSENT_VERSION`;
- `TERMS_VERSION`.

Факт принятия хранится в таблице `user_consents`.

## 8. Основные пользовательские разделы

Публичные страницы:

- `/` - лендинг;
- `/games` - публичный каталог игр;
- `/shop` - магазин;
- `/shop/<slug>` - страница товара;
- `/shop/thanks` - страница после оплаты;
- `/support` - поддержать проект;
- `/contacts` - контакты;
- `/delivery` - получение заказа;
- `/refund` - возврат;
- `/offer` - оферта;
- `/privacy`, `/consent`, `/terms` - юридические документы.

Закрытые разделы:

- `/login` - вход и регистрация;
- `/forgot-password` - запрос восстановления пароля;
- `/reset-password` - установка нового пароля;
- `/apps` - каталог активностей;
- `/apps/ege9` - тренажер задания 9;
- `/apps/ege10` - тренажер задания 10;
- `/apps/ege11` - тренажер задания 11;
- `/apps/mini` - каталог мини-игр внутри кабинета;
- `/apps/mini/games/<slug>` - игра в iframe внутри кабинета.

## 9. Активности и режимы тренировки

В `app/server.py` описан список `ACTIVITIES`:

- `ege9` - ЕГЭ. Задание 9;
- `ege10` - ЕГЭ. Задание 10;
- `ege11` - ЕГЭ. Задание 11;
- `html-games` - мини-игры.

На фронтенде в `app/static/app.js` есть режимы:

- `rule` - тренировка по выбранным правилам;
- `word_letter` - одно слово, ввод буквы и мгновенная проверка;
- `mix` - перемешанные орфограммы;
- `line` - формат строки с общей буквой для задания 9;
- `errors` - копилка ошибок.

Логика повторений:

- правильные ответы отмечаются в `word_progress`;
- ошибка добавляет `due_reviews`;
- `REPEAT_ON_ERROR = 3`, то есть ошибочное слово возвращается на повторение.

## 10. HTML-игры

Подключенные игры:

- `suffixes-nouns` - суффиксы существительных;
- `homogeneous-members-magic` - однородные члены предложения;
- `berry-season-ik-ek` - суффиксы ИК-ЕК.

Папки игр лежат в `app/HTML/`. Для части игр сохранены и русскоязычные исходные папки:

- `app/HTML/Пушинки/`;
- `app/HTML/Лето. Суффиксы/`;
- `app/HTML/Фокусы/`;
- `app/HTML/Ягодный сезон ИК-ЕК/`.

Сервер отдает игры двумя способами:

- `/html-games/<slug>/...` - игры для внутренней платформенной обертки;
- `/games/<slug>/...` - публичные игры без авторизации.

Учитель может создавать свои наборы:

- из баз ЕГЭ через `/api/games/sets/from-base`;
- загрузкой JSON через `/api/games/sets/upload-json`.

Созданные наборы хранятся в таблице `game_sets`, а посещения публичных игр - в `game_visits`.

## 11. Магазин

На фронтенде описаны товары в массиве `shopProducts` в `app/static/app.js`.

Текущий покупаемый товар:

- slug на фронтенде: `fruit-garden-ik-ek`;
- серверный продукт: `berry_season`;
- цена: `500.00 RUB`;
- публичное название: игра по суффиксам ИК-ЕК.

Реализованный сценарий покупки:

1. Пользователь нажимает "Купить".
2. Фронтенд открывает email-форму.
3. Запрос уходит на `/api/shop/berry-season/create-payment`.
4. Сервер создает платеж в ЮKassa.
5. Пользователь возвращается на `/shop/thanks?order=...`.
6. Сервер проверяет платеж через `/api/shop/berry-season/confirm-return`.
7. После подтверждения отправляет письмо со ссылкой на материал.
8. Если письмо не пришло, есть повторная отправка через `/api/shop/berry-season/resend-by-email`.

Доставка зависит от переменной `BERRY_SEASON_PRODUCT_URL`.

## 12. API

Авторизация:

- `POST /api/login`;
- `POST /api/auth/login`;
- `POST /api/register`;
- `POST /api/auth/register`;
- `POST /api/logout`;
- `POST /api/auth/logout`;
- `GET /api/me`;
- `GET /api/auth/me`;
- `POST /api/forgot-password`;
- `POST /api/auth/forgot-password`;
- `POST /api/reset-password`;
- `POST /api/auth/reset-password`.

Документы и согласия:

- `GET /api/documents/privacy`;
- `GET /api/documents/consent`;
- `GET /api/documents/terms`;
- `GET /api/public-documents/<slug>`;
- `GET /api/me/consents`;
- `POST /api/me/consents`.

Активности и тренировки:

- `GET /api/bootstrap`;
- `GET /api/activities`;
- `GET /api/apps/<slug>/bootstrap`;
- `POST /api/practice/start`;
- `POST /api/practice/check`;
- `POST /api/practice/submit`;
- `POST /api/apps/<slug>/practice/start`;
- `POST /api/apps/<slug>/practice/check`;
- `POST /api/apps/<slug>/practice/submit`.

Прогресс и тесты:

- `GET /api/progress`;
- `GET /api/progress/export?section=<section>`;
- `POST /api/teacher/test`.

Игры:

- `GET /api/games/sources`;
- `GET /api/games/sets/<public_id>`;
- `POST /api/games/sets/from-base`;
- `POST /api/games/sets/upload-json`.

Магазин:

- `POST /api/shop/berry-season/create-payment`;
- `POST /api/shop/berry-season/confirm-return`;
- `POST /api/shop/berry-season/resend-by-email`;
- `POST /api/yookassa/webhook`.

Админка:

- `GET /api/admin`;
- `POST /api/admin/test-email`;
- `POST /api/admin/reset-password`;
- `POST /api/admin/games/toggle`;
- `POST /api/heartbeat`.

## 13. База данных

Основная база: `data/ege_app.db`.

Таблицы, создаваемые сервером:

- `users` - пользователи, роли, email, коды учителя, хеши паролей;
- `attempts` - все попытки выполнения заданий;
- `word_progress` - индивидуальный прогресс по словам и повторения;
- `password_reset_tokens` - токены восстановления пароля;
- `documents` - версии документов;
- `user_consents` - принятые согласия;
- `game_sets` - созданные учителем публичные наборы для HTML-игр;
- `shop_orders` - заказы магазина и статусы ЮKassa;
- `game_visits` - посещения публичных игр.

В Docker база должна жить в volume `ege_platform_data`, а не в Git.

## 14. Важные функции frontend

`app/static/app.js` отвечает за:

- состояние приложения `state`;
- переключение публичной и закрытой оболочки;
- SPA-навигацию через `history.pushState`;
- рендер лендинга, игр, магазина, страниц документов;
- вход, регистрацию, восстановление пароля;
- экран обязательного согласия;
- каталог активностей;
- тренажеры и отправку ответов;
- прогресс, экспорт статистики;
- кабинет учителя и сборку теста;
- создание HTML-игр из баз или JSON;
- админку;
- heartbeat активных посетителей;
- модальное окно оплаты и страницу благодарности.

Ключевые блоки:

- `renderLandingPage`;
- `renderPublicGames`;
- `renderShopPlaceholder`, `renderShopProductPage`, `openBerrySeasonPaymentForm`;
- `restoreSession`;
- `renderDashboard`, `renderCatalog`, `renderMiniActivity`;
- `renderSetup`, `startPractice`, `renderLiveQuestion`, `submitPractice`;
- `showProgress`, `showTestComposer`;
- `renderAdminDashboard`, `bindAdminActions`.

## 15. Важные функции backend

`app/server.py` отвечает за:

- создание и миграцию SQLite-схемы: `ensure_app_db`;
- регистрацию и вход: `register_user`, `verify_password`;
- документы и согласия: `active_document`, `consent_status`, `record_user_consent`;
- bootstrap активностей: `activity_bootstrap`;
- маршрутизацию practice API: `activity_post`;
- генерацию вопросов: `make_word_question`, `make_line_question`;
- учет попыток: `record_attempt`;
- прогресс и статистику: `progress_for`, `progress_export`;
- админку: `admin_overview`;
- конструктор игр: `create_game_set_from_base`, `create_game_set_from_upload`;
- магазин: `create_berry_season_payment`, `deliver_berry_season_order`, `process_yookassa_webhook`;
- email: `send_password_reset_email`, `send_berry_season_email`, `send_email_message`;
- HTTP-роутинг: класс `Handler`.

## 16. Конфигурация окружения

Основной шаблон: `.env.example`.

Ключевые переменные:

- `APP_ENV`;
- `APP_BASE_URL`;
- `PORT`;
- `HOST`;
- `ADMIN_LOGIN`;
- `ADMIN_PASSWORD`;
- `SEED_DEMO_USERS`;
- `SMTP_HOST`;
- `SMTP_PORT`;
- `SMTP_USER`;
- `SMTP_PASSWORD`;
- `MAIL_FROM`;
- `SMTP_USE_SSL`;
- `YOOKASSA_SHOP_ID`;
- `YOOKASSA_SECRET_KEY`;
- `BERRY_SEASON_PRODUCT_URL`;
- `PRIVACY_POLICY_VERSION`;
- `CONSENT_VERSION`;
- `TERMS_VERSION`.

## 17. Локальный запуск

```bash
python app/server.py 127.0.0.1 8088
```

Открыть:

```text
http://127.0.0.1:8088
```

В development-режиме могут создаваться демо-пользователи:

- `admin` / `admin2026`;
- `teacher` / `teacher123`;
- `student` / `student123`.

## 18. Docker-запуск

```bash
docker compose up -d --build
docker compose logs -f app
docker compose down
```

Контейнер:

- имя: `ege-platform`;
- порт: `${PORT:-8088}:8088`;
- volume: `ege_platform_data:/app/data`;
- сеть: `ege_platform_net`.

## 19. Что нельзя коммитить

Нельзя коммитить:

- рабочую базу `data/ege_app.db`;
- дампы базы;
- реальные email пользователей;
- логи с персональными данными;
- `.env`;
- SMTP-пароли;
- ключи ЮKassa;
- любые секреты production.

Сейчас в репозитории есть локальная база и логи в `data/`, поэтому перед публикацией нужно отдельно проверить `.gitignore` и фактический git-статус на машине с установленным Git.

## 20. Замечания по состоянию проекта

- README немного устарел: в нем перечислены не все текущие публичные страницы, магазин, ЕГЭ-11 и обновленная система игр.
- Основной сервер использует стандартный `http.server`, не Flask.
- `app/ege10_module.py` и `app/ege11_module.py` содержат похожую серверную обвязку, но в актуальной архитектуре используются главным образом как модули логики для основного `app/server.py`.
- В `app/static/app.js` много данных магазина и текстов страниц прямо во фронтенде. Для маленького проекта это приемлемо, но при росте магазина лучше вынести товары в отдельный JSON/API.
- Git в текущем окружении не найден командой `git`, поэтому статус изменений автоматически проверить не удалось.
