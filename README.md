# vacation-workflow-demo

Прототип системы управления графиком отпусков на Django + Vue 3.

## Запуск
### Быстрый старт одной командой
- `make start` — установит зависимости, применит миграции и запустит dev-сервер на `http://localhost:8000/`.

### Готовые демо-учётки
- `make demo-users` создаст (или обновит) три тестовых учётки с паролем `password123`:
  - employee / password123 — сотрудник, менеджер назначен автоматически.
  - manager / password123 — руководитель для демо-сотрудника.
  - hr / password123 — кадровый сотрудник.

Авторизуйтесь любой из них через форму логина на SPA или через стандартный /admin (суперпользователь нужен отдельно).

### По шагам
1. Установите зависимости: `pip install -r requirements.txt` (или `make install`).
2. Примените миграции: `python vacation_workflow/manage.py migrate` (или `make migrate`).
3. Создайте суперпользователя: `python vacation_workflow/manage.py createsuperuser` (или `make superuser`).
4. Запустите сервер: `python vacation_workflow/manage.py runserver localhost:8000` (или `make run`).
5. Откройте `http://localhost:8000/` для доступа к SPA.

## Роли
- **employee** — видит свой остаток, подаёт и подтверждает заявки.
- **manager** — управляет заявками подчинённых (поле manager у пользователя).
- **hr** — видит все заявки и может выгружать утверждённые в CSV.

API эндпоинты находятся под префиксом `/api/` и используют cookie-сессии и CSRF-защиту Django.
