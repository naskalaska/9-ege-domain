# Deploy on Render

This folder contains the full web app, not the Streamlit backup.

Render settings:

- Runtime: Python
- Build command: `pip install -r requirements.txt`
- Start command: `python app/server.py 0.0.0.0 $PORT`

The app uses only the Python standard library. User progress is stored in
`data/ege_app.db`; on Render free instances, local SQLite storage may be reset
when the service is redeployed or restarted.

Development demo accounts are created only when `SEED_DEMO_USERS=1` or when
the app runs outside production mode. Do not enable these accounts in
production.

Demo accounts:

- Teacher: `teacher` / `teacher123`
- Student: `student` / `student123`

Teacher code for demo students: `TEACHER-2026`


## Перед приёмом реальных оплат

Укажите переменные в окружении сервиса: `APP_ENV=production`, `SEED_DEMO_USERS=0`,
`APP_BASE_URL=https://ваш-домен`, `ADMIN_LOGIN`, надёжный `ADMIN_PASSWORD`,
настройки ЮKassa и SMTP. Сам Python-сервер файл `.env` не загружает.
Текущий `render.yaml` задаёт бесплатный план и не задаёт эти переменные.

Рабочий путь базы в коде: `<корень проекта>/data/ege_app.db`.
`DATABASE_PATH` и `DATABASE_URL` сейчас не меняют этот путь.
Подключите постоянный диск именно к каталогу `data` проекта на сервере
либо отдельно реализуйте смену пути базы. Пустая переменная окружения без
изменения кода не переносит базу на диск. Бесплатный план Render не поддерживает
постоянные диски; для рабочего платного курса текущая бесплатная конфигурация
не подходит. Тариф в этом изменении автоматически не переключался.

Перед миграцией сохраните резервную копию SQLite; не загружайте тестовую базу
`data/course-preview/ege_app.db` и локальную базу с демонстрационными аккаунтами.
После рестарта проверьте сохранность заказа, группы и прогресса, а также повторный вход:
сессии авторизации хранятся в памяти процесса и не переживают перезапуск.

Подробный аудит: [maintenance/COURSE_DEPLOY_AUDIT_2026-11-25.md](maintenance/COURSE_DEPLOY_AUDIT_2026-11-25.md).
