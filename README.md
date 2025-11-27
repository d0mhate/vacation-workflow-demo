# vacation-workflow-demo

Прототип системы управления графиком отпусков на Django + Vue 3 (сборка через Vite).

Документация моделей: [docs/models.md](docs/models.md).

## Запуск
### Быстрый старт
- Docker (рекомендуется): `make up` - соберёт образ, поднимет контейнер через docker-compose и откроет `http://localhost:8000/static/index.html`.
- Локально (без Docker):
  - `make start` - установит зависимости, применит миграции и запустит dev-сервер на `http://localhost:8000/static/index.html`.
  - `make fe-install && make fe-build` - собрать фронт (Vue + Vite) в `static/dist`. Для разработки фронта есть `make fe-dev`.

### Готовые демо-учётки
- `make demo-users` создаст (или обновит) три тестовых учётки с паролем `password123`:
  - employee / password123 - сотрудник, менеджер назначен автоматически.
  - manager / password123 - руководитель для демо-сотрудника.
  - hr / password123 - кадровый сотрудник.

Авторизуйтесь любой из них через форму логина на SPA или через стандартный /admin (суперпользователь нужен отдельно).
Для живой работы фронта используйте путь `http://localhost:8000/static/index.html` (SPA с бандлом из `static/dist`).

### По шагам
1. Установите зависимости: `pip install -r requirements.txt` (или `make install`).
2. Примените миграции: `python vacation_workflow/manage.py migrate` (или `make migrate`).
3. Соберите фронт: `make fe-install && make fe-build`.
4. Создайте суперпользователя: `python vacation_workflow/manage.py createsuperuser` (или `make superuser`).
5. Запустите сервер: `python vacation_workflow/manage.py runserver localhost:8000` (или `make run`).
6. Откройте `http://localhost:8000/static/index.html` для доступа к SPA (или `make open-url`).

### Запуск в Docker
1. Соберите образ: `make docker-build` (или `docker build -t d0mhate/vacation-workflow .`).
2. Запустите контейнер: `make docker-run` (поднимется на `http://localhost:8000`, SPA на `/static/index.html`).
3. Остановить/логи: `make docker-stop`, `make docker-logs`.
4. Одной командой: `make up` - build+up+подсказки, откроет браузер.

Готовый образ в Docker Hub: `d0mhate/vacation-workflow:latest`
- `docker pull d0mhate/vacation-workflow:latest`
- `docker run --rm -p 8000:8000 d0mhate/vacation-workflow:latest` (SPA на `http://localhost:8000/static/index.html`)

### Запуск через docker-compose
- `make compose-up` - соберёт образ и поднимет контейнер `app` на `http://localhost:8000`.
- `make compose-logs` - смотреть логи.
- `make compose-down` - остановить.

### Режим разработки с монтированием кода (docker-compose.dev.yml)
- `make compose-dev-up` - запустить с volume текущей директории (`.` монтируется в /app), удобно для живой правки кода.
- `make compose-dev-logs` - смотреть логи.
- `make compose-dev-down` - остановить.
> Примечание: node_modules и dist внутри контейнера исключены из volume (аналогично прописано в docker-compose.dev.yml).

## Роли
- **employee** - видит свой остаток, подаёт и подтверждает заявки.
- **manager** - управляет заявками подчинённых (поле manager у пользователя).
- **hr** - видит все заявки и может выгружать утверждённые в CSV.

API эндпоинты находятся под префиксом `/api/` и используют cookie-сессии и CSRF-защиту Django. Для лайв-обновлений используется SSE (`/api/live/sse`).

## Возможности проекта

- Основные потоки заявок: подача, редактирование, дублирование, удаление, рассмотрение и подтверждение отпусков.
- Управление остатками отпусков сотрудников.
- Уведомления о новых и изменённых заявках + SSE для live-обновлений интерфейса (данные подтягиваются без ручного обновления).
- График отпусков с отображением занятости, календарная таблица и CSV/печатные выгрузки для HR (с фильтрами по году и подразделению).
- Печатные формы для графика отпусков.
- Inline-редактирование некоторых полей в интерфейсе.
- Cron-задачи для отправки уведомлений и напоминаний.
- Ролевой доступ с разграничением прав для сотрудников, менеджеров и HR.

## Функции по ролям

### Employee
- Просмотр собственного остатка отпусков.
- Подача новых заявок на отпуск.
- Редактирование, удаление (pending) и дублирование своих заявок.
- Подтверждение ознакомления.

### Manager
- Просмотр и управление заявками подчинённых.
- Одобрение или отклонение заявок сотрудников.
- Получение уведомлений о новых заявках.

### HR
- Просмотр всех заявок по всем сотрудникам.
- Выгрузка утверждённых заявок в CSV.
- Годовой график по месяцам + фильтр по подразделению, выгрузка графика в CSV и принт-версия.

## Команды Makefile (backend + frontend)

- `make start` - установка зависимостей, миграции, запуск Django.
- `make install` - Python-зависимости из requirements.txt.
- `make migrate` - применить миграции.
- `make run` - запуск Django dev-сервера.
- `make superuser` - создать суперпользователя.
- `make demo-users` - создать/обновить тестовые учётки.
- `make notifications` - сгенерировать уведомления (management command).
- `make reset-db` - сброс БД и миграции.
- `make fe-install` - npm install в `frontend/`.
- `make fe-build` - сборка Vite в `vacation_workflow/static/dist`.
- `make fe-dev` - Vite dev server (нужен прокси к API или ручной запуск Django).
- `make fe-clean` - удалить dist/node_modules фронта.

## Что реализовано и что нет

**Реализовано:**
- Основные сценарии подачи и обработки заявок.
- Управление остатками отпусков.
- Ролевой доступ и разграничение прав.
- Уведомления и напоминания.
- Интерфейс с Vue 3 и backend на Django.

**Не реализовано:**
- Полностью автоматизированные печатные формы.
- Расширенное inline-редактирование.
- Поддержка сложных графиков и календарей.
- Расширенные настройки уведомлений и интеграции.
- Масштабируемость и оптимизация производительности.
