# ЕГЭ: платформа активностей

Единое приложение для учебных активностей на одном домене: общий вход, роли `admin`, `teacher`, `student`, единая SQLite-база пользователей и общий журнал попыток.

Сейчас внутри платформы подключены:

- `/apps/ege9` - тренажер "ЕГЭ. Задание 9";
- `/apps/ege10` - тренажер "ЕГЭ. Задание 10";
- `/apps/mini/demo-mini` - демонстрационная обертка для HTML-мини-приложений.

## Локальный запуск

```bash
pip install -r requirements.txt
python app/server.py 127.0.0.1 8088
```

Откройте `http://127.0.0.1:8088`.

В development-режиме создаются демо-пользователи:

- `admin` / `admin2026`
- `teacher` / `teacher123`
- `student` / `student123`

## Переменные окружения

Скопируйте `.env.example` в `.env` и замените секреты.

Минимально важные переменные:

- `APP_ENV=production`
- `APP_BASE_URL=https://dimitrieva-av.ru`
- `ADMIN_LOGIN=admin@example.com`
- `ADMIN_PASSWORD=<long-random-password>`
- `SEED_DEMO_USERS=0`
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `MAIL_FROM`

Пароли пользователей хранятся только как PBKDF2-SHA256 hash. Старые SHA-256-хеши поддерживаются для входа и обновляются после успешной авторизации.

## Маршруты

- `/` - каталог активностей после входа;
- `/login` - вход;
- `/admin` - админский кабинет;
- `/teacher` - кабинет учителя;
- `/apps/ege9` - модуль задания 9;
- `/apps/ege10` - модуль задания 10;
- `/apps/mini/<slug>` - HTML-мини-приложение внутри платформенной обертки.

## API

Основные группы API:

- `/api/auth/login`, `/api/auth/logout`, `/api/auth/me`
- `/api/activities`
- `/api/apps/ege9/bootstrap`
- `/api/apps/ege9/practice/start`, `/submit`, `/check`
- `/api/apps/ege10/bootstrap`
- `/api/apps/ege10/practice/start`, `/submit`, `/check`
- `/api/progress`, `/api/progress/export`
- `/api/admin`, `/api/admin/reset-password`
- `/api/teacher/test`

Старые маршруты `/api/login`, `/api/bootstrap`, `/api/practice/*` оставлены для совместимости с модулем ЕГЭ 9.

## Как добавить новую activity

1. Добавьте запись в `ACTIVITIES` в `app/server.py`.
2. Для большого модуля добавьте API-маршруты `/api/apps/<slug>/...`.
3. Для HTML-мини-приложения добавьте папку со статикой и откройте ее через `/apps/mini/<slug>` в платформенной обертке.
4. Пишите попытки в общую таблицу `attempts`, чтобы прогресс был доступен учителю и администратору.

## Docker и Portainer

```bash
docker compose up -d --build
docker compose logs -f app
docker compose down
```

SQLite хранится в volume `ege_platform_data` по пути `/app/data/ege_app.db`, поэтому данные не пропадают после redeploy.

Для домена оставьте один proxy:

```text
dimitrieva-av.ru -> 127.0.0.1:8088
```

Поддомены и отдельные контейнеры для `ege9`/`ege10` не нужны.
## Персональные данные

Публичные страницы документов доступны без авторизации:

- `/privacy`
- `/consent`
- `/terms`

Текущие версии задаются переменными окружения:

- `PRIVACY_POLICY_VERSION=2026-06-02`
- `CONSENT_VERSION=2026-06-02`
- `TERMS_VERSION=2026-06-02`

Документы хранятся в таблице `documents`, факт принятия - в таблице `user_consents`:

- `user_id`
- `consent_type`
- `document_version`
- `accepted_at`
- `ip_address`
- `user_agent`

При регистрации пользователь обязан поставить чекбокс согласия. Без чекбокса сервер отклоняет регистрацию. Пользователь, созданный администратором или учителем и не имеющий актуального согласия, после входа видит экран принятия документов и не может открыть каталог или запустить тренажеры до принятия.

Тексты Политики обработки персональных данных и Согласия на обработку персональных данных являются шаблонами и должны быть заменены на финальные юридически выверенные тексты перед запуском регистрации реальных пользователей.

Рабочая SQLite-база с пользователями, прогрессом и согласиями должна храниться только на сервере/VPS в Санкт-Петербурге в Docker volume `ege_platform_data`. Нельзя коммитить в GitHub рабочую базу, дампы базы, реальные email пользователей, логи с персональными данными, `.env`, секреты и `SMTP_PASSWORD`.
