# Модели домена

Описание Django-моделей из `vacation_workflow/vacation_app/models.py`.

## User (наследник `AbstractUser`)
- `role` (`CharField`, выборы `employee|manager|hr`, по умолчанию `employee`): бизнес-роль пользователя.
- `manager` (`ForeignKey` на `User`, `SET_NULL`, `related_name="team_members"`, допускает `null`/`blank`): руководитель сотрудника.
- `first_name`, `last_name` (`CharField`, допускают `blank`): имя и фамилия, можно оставить пустыми.
- `updated_at` (`DateTimeField`, `auto_now=True`): метка последнего обновления профиля.

## VacationRequest
- `user` (`ForeignKey` на `User`, `CASCADE`, `related_name="vacation_requests"`): владелец заявки.
- `start_date`, `end_date` (`DateField`): запрошенный период отпуска.
- `status` (`CharField`, выборы `pending|approved|rejected`, по умолчанию `pending`): статус согласования.
- `created_at` (`DateTimeField`, `auto_now_add=True`), `updated_at` (`DateTimeField`, `auto_now=True`): системные метки создания/обновления.
- `confirmed_by_employee` (`BooleanField`, по умолчанию `False`): признак, что сотрудник подтвердил изменения после правок менеджера/HR.

## VacationSchedule
- `user` (`ForeignKey` на `User`, `CASCADE`, `related_name="vacation_schedules"`): владелец графика.
- `year` (`PositiveIntegerField`): год графика.
- `period_from`, `period_to` (`DateField`): выбранный период отпуска по графику.

## Notification
- `user` (`ForeignKey` на `User`, `CASCADE`, `related_name="notifications"`): получатель уведомления.
- `type` (`CharField`, выборы `request_created|request_approved|request_rejected|reminder_upcoming|request_rescheduled`, по умолчанию `request_created`): тип уведомления.
- `request` (`ForeignKey` на `VacationRequest`, допускает `null`/`blank`, `CASCADE`): связанная заявка (если есть).
- `is_read` (`BooleanField`, по умолчанию `False`): прочитано/непрочитано.
- `created_at` (`DateTimeField`, `auto_now_add=True`): время создания уведомления.

## VacationBalance
- `user` (`ForeignKey` на `User`, `CASCADE`, `related_name="vacation_balances"`): владелец баланса.
- `year` (`IntegerField`, по умолчанию `2025`): год баланса.
- `days_remaining` (`PositiveIntegerField`, по умолчанию `0`): оставшиеся дни отпуска.
- Meta: `unique_together` для `(user, year)`; сортировка по убыванию года (`ordering = ['-year']`).
