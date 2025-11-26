import csv
import json

from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.middleware import csrf
from django.utils.html import escape
from .models import User, VacationRequest, Notification, VacationBalance
from datetime import date, datetime
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.contrib.auth.decorators import login_required

from .models import (
    Notification,
    User,
    VacationBalance,
    VacationRequest,
)


ROLE_EMPLOYEE = User.Roles.EMPLOYEE
ROLE_MANAGER = User.Roles.MANAGER
ROLE_HR = User.Roles.HR


def _json_error(message, status=400):
    return JsonResponse({'error': message}, status=status)


def _get_request_data(request):
    try:
        return json.loads(request.body.decode() or '{}')
    except json.JSONDecodeError:
        return {}


def _require_role(user, role):
    return user.is_authenticated and user.role == role


@require_POST
def login_view(request):
    data = _get_request_data(request)
    username = data.get('username')
    password = data.get('password')
    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        return JsonResponse({'message': 'Logged in', 'user': _serialize_user(user)})
    return _json_error('Invalid credentials', status=401)


@require_POST
def logout_view(request):
    logout(request)
    return JsonResponse({'message': 'Logged out'})


@require_GET
def me(request):
    csrf.get_token(request)  # ensure CSRF cookie is set
    if request.user.is_authenticated:
        return JsonResponse({'authenticated': True, 'user': _serialize_user(request.user)})
    return JsonResponse({'authenticated': False})


@login_required
@require_GET
def vacation_balance(request):
    if request.user.role != ROLE_EMPLOYEE:
        return HttpResponseForbidden()

    # текущий год — для карточки "Остаток отпусков"
    current_year = date.today().year

    balance, _ = VacationBalance.objects.get_or_create(
        user=request.user,
        year=current_year,
        defaults={'days_remaining': 0},
    )

    data = _serialize_balance(balance)
    return JsonResponse(data)


@login_required
@require_GET
def my_requests(request):
    if request.user.role != ROLE_EMPLOYEE:
        return HttpResponseForbidden()
    requests = VacationRequest.objects.filter(user=request.user).order_by('-created_at')
    return JsonResponse({'requests': [_serialize_request(req) for req in requests]})


@login_required
@require_POST
def update_request(request, pk):
    """Редактирование своей заявки на отпуск, пока она в статусе PENDING."""
    if request.user.role != ROLE_EMPLOYEE:
        return HttpResponseForbidden()

    manager = getattr(request.user, "manager", None)

    # Ищем заявку только текущего пользователя
    try:
        vacation_request = VacationRequest.objects.get(pk=pk, user=request.user)
    except VacationRequest.DoesNotExist:
        return _json_error('Заявка не найдена', status=404)

    # Разрешаем редактировать только заявки в статусе PENDING
    if vacation_request.status != VacationRequest.Status.PENDING:
        return _json_error('Редактировать можно только заявки в статусе "На согласовании"', status=400)

    data = _get_request_data(request)
    start_date_str = data.get('start_date')
    end_date_str = data.get('end_date')

    if not start_date_str or not end_date_str:
        return _json_error('start_date и end_date обязательны для редактирования')

    try:
        start_date = date.fromisoformat(start_date_str)
        end_date = date.fromisoformat(end_date_str)
    except ValueError:
        return _json_error('Неверный формат даты. Ожидается YYYY-MM-DD')

    # базовая проверка диапазона
    if end_date < start_date:
        return _json_error('Дата окончания не может быть раньше даты начала')

    # количество дней в заявке (включая обе даты)
    days_requested = (end_date - start_date).days + 1

    # проверяем фактический остаток за год начала отпуска
    year = start_date.year
    balance = VacationBalance.objects.filter(user=request.user, year=year).first()
    if balance:
        initial_days = balance.days_remaining
        planned_days = _calculate_planned_days(request.user, year)
        available = max(initial_days - planned_days, 0)
    else:
        available = 0

    if days_requested > available:
        return _json_error(
            f'Недостаточно дней отпуска на {year} год. Доступно: {available}, выбрано: {days_requested}.',
            status=400,
        )

    # Обновляем заявку
    vacation_request.start_date = start_date
    vacation_request.end_date = end_date
    vacation_request.save(update_fields=['start_date', 'end_date'])

    # Уведомляем менеджера, если есть
    if manager:
        _create_notification(
            user=manager,
            type=Notification.Type.REQUEST_RESCHEDULED,
            request=vacation_request,
        )

    return JsonResponse({'request': _serialize_request(vacation_request)})


@login_required
@require_POST
def confirm_request(request, pk):
    if request.user.role != ROLE_EMPLOYEE:
        return HttpResponseForbidden()
    try:
        vacation_request = VacationRequest.objects.get(pk=pk, user=request.user)
    except VacationRequest.DoesNotExist:
        return _json_error('Request not found', status=404)
    vacation_request.confirmed_by_employee = True
    vacation_request.save(update_fields=['confirmed_by_employee'])
    return JsonResponse({'request': _serialize_request(vacation_request)})


@login_required
@require_GET
def manager_requests(request):
    if request.user.role != ROLE_MANAGER:
        return HttpResponseForbidden()
    requests = VacationRequest.objects.filter(user__manager=request.user).select_related('user').order_by('-created_at')
    return JsonResponse({'requests': [_serialize_request(req) for req in requests]})


@login_required
@require_POST
def manager_approve(request, pk):
    if request.user.role != ROLE_MANAGER:
        return HttpResponseForbidden()
    try:
        vacation_request = VacationRequest.objects.get(pk=pk, user__manager=request.user)
    except VacationRequest.DoesNotExist:
        return _json_error('Request not found', status=404)
    vacation_request.status = VacationRequest.Status.APPROVED
    vacation_request.save(update_fields=['status'])
    _create_notification(
        user=vacation_request.user,
        type=Notification.Type.REQUEST_APPROVED,
        request=vacation_request,
    )
    return JsonResponse({'request': _serialize_request(vacation_request)})


@login_required
@require_POST
def manager_reject(request, pk):
    if request.user.role != ROLE_MANAGER:
        return HttpResponseForbidden()
    try:
        vacation_request = VacationRequest.objects.get(pk=pk, user__manager=request.user)
    except VacationRequest.DoesNotExist:
        return _json_error('Request not found', status=404)
    vacation_request.status = VacationRequest.Status.REJECTED
    vacation_request.save(update_fields=['status'])
    _create_notification(
        user=vacation_request.user,
        type=Notification.Type.REQUEST_REJECTED,
        request=vacation_request,
    )
    return JsonResponse({'request': _serialize_request(vacation_request)})


@login_required
@require_GET
def hr_requests(request):
    if request.user.role != ROLE_HR:
        return HttpResponseForbidden()
    requests = VacationRequest.objects.select_related('user').order_by('-created_at')
    return JsonResponse({'requests': [_serialize_request(req) for req in requests]})


@login_required
@require_GET
def hr_export(request):
    if request.user.role != ROLE_HR:
        return HttpResponseForbidden()
    approved_requests = VacationRequest.objects.filter(status=VacationRequest.Status.APPROVED).select_related('user')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="vacation_approved.csv"'
    writer = csv.writer(response)
    writer.writerow(['ID', 'Employee', 'Start Date', 'End Date', 'Status', 'Created At', 'Confirmed'])
    for req in approved_requests:
        writer.writerow([
            req.id,
            req.user.username,
            req.start_date,
            req.end_date,
            req.status,
            req.created_at,
            req.confirmed_by_employee,
        ])
    return response

@login_required
@require_GET
def hr_schedule(request):
    # Только HR имеет доступ
    if getattr(request.user, "role", None) != "hr":
        return JsonResponse({"error": "Forbidden"}, status=403)

    # Год берём из query-параметра ?year=2025, если нет — текущий
    try:
        year = int(request.GET.get("year") or date.today().year)
    except ValueError:
        year = date.today().year

    manager_id_raw = request.GET.get("manager_id")
    manager_id = None
    if manager_id_raw:
        try:
            manager_id = int(manager_id_raw)
        except ValueError:
            manager_id = None

    entries = _get_hr_schedule_entries(year=year, manager_id=manager_id)

    return JsonResponse({
        "year": year,
        "entries": entries,
    })


def _get_hr_schedule_entries(year: int, manager_id: int | None = None):
    qs = (
        VacationRequest.objects
        .filter(
            start_date__year=year,
            status="approved",  # только согласованные
        )
        .select_related("user", "user__manager")
        .order_by("user__last_name", "user__first_name", "start_date")
    )

    if manager_id:
        qs = qs.filter(user__manager_id=manager_id)

    schedule = {}
    for req in qs:
        u = req.user
        key = u.id
        manager = getattr(u, "manager", None)
        manager_name = ""
        if manager:
            manager_name = (f"{manager.first_name} {manager.last_name}".strip() or manager.username).strip()
        if key not in schedule:
            full_name = (f"{u.first_name} {u.last_name}".strip() or u.username).strip()
            schedule[key] = {
                "user_id": u.id,
                "username": u.username,
                "full_name": full_name,
                "manager_id": manager.id if manager else None,
                "manager_name": manager_name,
                "periods": [],
            }
        days = (req.end_date - req.start_date).days + 1
        schedule[key]["periods"].append({
            "id": req.id,
            "start_date": req.start_date.isoformat(),
            "end_date": req.end_date.isoformat(),
            "confirmed_by_employee": req.confirmed_by_employee,
            "days": days,
        })

    return list(schedule.values())


@login_required
@require_GET
def hr_schedule_export(request):
    if getattr(request.user, "role", None) != "hr":
        return JsonResponse({"error": "Forbidden"}, status=403)

    try:
        year = int(request.GET.get("year") or date.today().year)
    except ValueError:
        year = date.today().year

    manager_id_raw = request.GET.get("manager_id")
    try:
        manager_id = int(manager_id_raw) if manager_id_raw else None
    except ValueError:
        manager_id = None

    entries = _get_hr_schedule_entries(year=year, manager_id=manager_id)

    response = HttpResponse(content_type='text/csv')
    filename = f"vacation_schedule_{year}.csv"
    if manager_id:
        filename = f"vacation_schedule_{year}_manager_{manager_id}.csv"
    response['Content-Disposition'] = f'attachment; filename=\"{filename}\"'

    writer = csv.writer(response)
    writer.writerow([
        'Сотрудник (логин)', 'ФИО', 'Менеджер', 'Начало отпуска',
        'Конец отпуска', 'Дней', 'Подтверждено сотрудником'
    ])
    for entry in entries:
        for period in entry.get("periods", []):
            writer.writerow([
                entry.get("username", ""),
                entry.get("full_name", ""),
                entry.get("manager_name", ""),
                period.get("start_date", ""),
                period.get("end_date", ""),
                period.get("days", ""),
                "Да" if period.get("confirmed_by_employee") else "Нет",
            ])
    return response


@login_required
@require_GET
def hr_schedule_print(request):
    if getattr(request.user, "role", None) != "hr":
        return JsonResponse({"error": "Forbidden"}, status=403)

    try:
        year = int(request.GET.get("year") or date.today().year)
    except ValueError:
        year = date.today().year

    manager_id_raw = request.GET.get("manager_id")
    try:
        manager_id = int(manager_id_raw) if manager_id_raw else None
    except ValueError:
        manager_id = None

    entries = _get_hr_schedule_entries(year=year, manager_id=manager_id)

    rows_html = []
    for entry in entries:
        period_chunks = []
        for p in entry.get("periods", []):
            confirm_suffix = "" if p.get("confirmed_by_employee") else " <span class=\"chip-sub\">без подтверждения</span>"
            period_chunks.append(
                f"<div class='chip'>{escape(p['start_date'])} — {escape(p['end_date'])} ({p['days']} дн.){confirm_suffix}</div>"
            )
        periods_html = "".join(period_chunks) or "<div class='muted'>Нет утверждённых периодов</div>"
        rows_html.append(
            "<tr>"
            f"<td><div class='user-name'>{escape(entry.get('full_name',''))}</div>"
            f"<div class='muted'>{escape(entry.get('username',''))}</div>"
            f"<div class='muted small'>{escape(entry.get('manager_name',''))}</div></td>"
            f"<td>{periods_html}</td>"
            "</tr>"
        )

    manager_label = ""
    if manager_id:
        manager_obj = User.objects.filter(id=manager_id, role=ROLE_MANAGER).first()
        if manager_obj:
            manager_label = f" • Подразделение: {(manager_obj.first_name + ' ' + manager_obj.last_name).strip() or manager_obj.username}"

    html_content = f"""
    <!doctype html>
    <html>
      <head>
        <meta charset="utf-8" />
        <title>График отпусков {year}</title>
        <style>
          body {{ font-family: Arial, sans-serif; margin: 24px; }}
          h1 {{ margin-bottom: 4px; }}
          .muted {{ color: #666; font-size: 12px; }}
          .small {{ font-size: 11px; }}
          table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
          th, td {{ border: 1px solid #ddd; padding: 8px; vertical-align: top; }}
          th {{ background: #f7f7f7; text-align: left; }}
          .chip {{ display: inline-block; padding: 4px 8px; background: #eef6ff; border: 1px solid #d3e5ff; border-radius: 12px; margin: 2px; }}
          .chip-sub {{ color: #a94442; font-size: 11px; }}
          .user-name {{ font-weight: 600; }}
          @media print {{
            button {{ display: none; }}
            body {{ margin: 0; padding: 0; }}
          }}
        </style>
      </head>
      <body>
        <h1>График отпусков на {year} год</h1>
        <div class="muted">Только согласованные заявки{escape(manager_label)}</div>
        <table>
          <thead>
            <tr><th>Сотрудник</th><th>Периоды</th></tr>
          </thead>
          <tbody>
            {''.join(rows_html)}
          </tbody>
        </table>
        <button onclick="window.print()">Печать</button>
      </body>
    </html>
    """
    return HttpResponse(html_content)


@login_required
@require_GET
def hr_departments(request):
    if getattr(request.user, "role", None) != "hr":
        return JsonResponse({"error": "Forbidden"}, status=403)
    managers = User.objects.filter(role=ROLE_MANAGER).order_by("last_name", "first_name")
    data = []
    for m in managers:
        full_name = (f"{m.first_name} {m.last_name}".strip() or m.username).strip()
        data.append({
            "id": m.id,
            "username": m.username,
            "full_name": full_name,
        })
    return JsonResponse({"departments": data})


@login_required
@require_GET
def notifications_list(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    return JsonResponse({'notifications': [_serialize_notification(n) for n in notifications]})


@login_required
@require_GET
def notifications_unread_count(request):
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'unread_count': count})


@login_required
@require_POST
def notification_mark_read(request, pk):
    try:
        notification = Notification.objects.get(pk=pk, user=request.user)
    except Notification.DoesNotExist:
        return _json_error('Notification not found', status=404)
    notification.is_read = True
    notification.save(update_fields=['is_read'])
    return JsonResponse({'notification': _serialize_notification(notification)})


def _serialize_user(user: User):
    return {
        'id': user.id,
        'username': user.username,
        'first_name': user.first_name or '',
        'last_name': user.last_name or '',
        'role': user.role,
        'manager_id': user.manager_id,
    }


def _calculate_planned_days(user: User, year: int) -> int:
    """Считает количество дней уже утверждённых и подтверждённых заявок за указанный год."""
    qs = VacationRequest.objects.filter(
        user=user,
        start_date__year=year,
        status=VacationRequest.Status.APPROVED,
        confirmed_by_employee=True,
    )
    total_days = 0
    for req in qs:
        total_days += (req.end_date - req.start_date).days + 1
    return total_days


def _serialize_balance(balance: VacationBalance):
    initial_days = balance.days_remaining
    planned_days = _calculate_planned_days(balance.user, balance.year)
    remaining_days = max(initial_days - planned_days, 0)
    return {
        'id': balance.id,
        'year': balance.year,
        'initial_days': initial_days,
        'planned_days': planned_days,
        'remaining_days': remaining_days,
        # для обратной совместимости с фронтом
        'days_remaining': remaining_days,
        'user': _serialize_user(balance.user),
    }

def _serialize_request(request_obj: VacationRequest):
    return {
        'id': request_obj.id,
        'user': _serialize_user(request_obj.user),
        'start_date': request_obj.start_date.isoformat(),
        'end_date': request_obj.end_date.isoformat(),
        'status': request_obj.status,
        'created_at': request_obj.created_at.isoformat(),
        'confirmed_by_employee': request_obj.confirmed_by_employee,
    }


def _serialize_notification(notification: Notification):
    return {
        'id': notification.id,
        'type': notification.type,
        'request_id': notification.request.id if notification.request else None,
        'message': _build_notification_message(notification),
        'is_read': notification.is_read,
        'created_at': notification.created_at.isoformat(),
    }


def _build_notification_message(notification: Notification):
    req = notification.request

    # Пользователь, который видит уведомление (получатель)
    viewer = notification.user

    # Будем показывать имя сотрудника только, если уведомление читает не он сам
    employee_label = ""
    is_self = False

    if req and req.user:
        u = req.user
        full_name = (f"{u.first_name} {u.last_name}".strip() or u.username).strip()
        is_self = (viewer.id == u.id)

        if not is_self:
            employee_label = f" сотрудника {full_name}"

    # Далее тексты зависят и от типа уведомления, и от того, кто его читает

    if notification.type == Notification.Type.REQUEST_APPROVED and req:
        if is_self:
            return (
                f"Ваша заявка №{req.id} на отпуск "
                f"с {req.start_date.isoformat()} по {req.end_date.isoformat()} — согласована менеджером."
            )
        return (
            f"Заявка №{req.id}{employee_label} на отпуск "
            f"с {req.start_date.isoformat()} по {req.end_date.isoformat()} — согласована менеджером."
        )

    if notification.type == Notification.Type.REQUEST_REJECTED and req:
        if is_self:
            return (
                f"Ваша заявка №{req.id} на отпуск "
                f"с {req.start_date.isoformat()} по {req.end_date.isoformat()} — отклонена менеджером."
            )
        return (
            f"Заявка №{req.id}{employee_label} на отпуск "
            f"с {req.start_date.isoformat()} по {req.end_date.isoformat()} — отклонена менеджером."
        )

    if notification.type == Notification.Type.REQUEST_CREATED and req:
        if is_self:
            return (
                f"Вы создали заявку №{req.id} на отпуск "
                f"({req.start_date.isoformat()} — {req.end_date.isoformat()})."
            )
        return (
            f"Создана новая заявка №{req.id}{employee_label} на отпуск "
            f"({req.start_date.isoformat()} — {req.end_date.isoformat()})."
        )

    if notification.type == Notification.Type.REQUEST_RESCHEDULED and req:
        if is_self:
            return (
                f"Вы изменили период заявки №{req.id} на отпуск. "
                f"Новый период: {req.start_date.isoformat()} — {req.end_date.isoformat()}."
            )
        return (
            f"Сотрудник{employee_label} изменил период заявки №{req.id} на отпуск. "
            f"Новый период: {req.start_date.isoformat()} — {req.end_date.isoformat()}."
        )

    if notification.type == "vacation_reminder_14d" and req:
        if is_self:
            return (
                f"До начала вашего отпуска №{req.id} осталось 14 дней "
                f"({req.start_date.isoformat()} — {req.end_date.isoformat()})."
            )
        return (
            f"До начала отпуска №{req.id}{employee_label} осталось 14 дней "
            f"({req.start_date.isoformat()} — {req.end_date.isoformat()})."
        )

    if notification.type == "vacation_start_today" and req:
        if is_self:
            return (
                f"Сегодня начинается ваш отпуск №{req.id} "
                f"({req.start_date.isoformat()} — {req.end_date.isoformat()})."
            )
        return (
            f"Сегодня начинается отпуск №{req.id}{employee_label} "
            f"({req.start_date.isoformat()} — {req.end_date.isoformat()})."
        )

    return "Уведомление"


def _create_notification(user: User, type: str, request: VacationRequest = None):
    Notification.objects.create(
        user=user,
        type=type,
        request=request
    )

@login_required
@require_POST
def profile_update(request):
    data = _get_request_data(request)
    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()

    if not first_name or not last_name:
        return _json_error('Имя и фамилия обязательны')

    user = request.user
    user.first_name = first_name
    user.last_name = last_name
    user.save(update_fields=['first_name', 'last_name'])

    return JsonResponse({'user': _serialize_user(user)})

@login_required
@require_GET
def vacation_balances(request):
    user = request.user
    qs = VacationBalance.objects.select_related('user')

    # Разные выборки по ролям
    if user.role == User.Roles.EMPLOYEE:
        qs = qs.filter(user=user)
    elif user.role == User.Roles.MANAGER:
        # все сотрудники, у которых этот пользователь — менеджер
        qs = qs.filter(user__manager=user)
    elif user.role == User.Roles.HR:
        # кадровик видит всех
        pass
    else:
        qs = qs.none()

    data = [_serialize_balance(b) for b in qs]
    return JsonResponse({'balances': data})

@login_required
@require_http_methods(["POST"])
def create_request(request):
    """
    Создание новой заявки на отпуск сотрудником.
    Проверяем:
    - корректность дат
    - что конец не раньше начала
    - что запрошено не больше доступного остатка по году начала отпуска
    """
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Некорректный JSON"}, status=400)

    start_str = payload.get("start_date")
    end_str = payload.get("end_date")

    if not start_str or not end_str:
        return JsonResponse(
            {"error": "Нужно указать даты начала и конца отпуска"},
            status=400,
        )

    try:
        start_date = date.fromisoformat(start_str)
        end_date = date.fromisoformat(end_str)
    except ValueError:
        return JsonResponse(
            {"error": "Неверный формат дат (ожидается ГГГГ-ММ-ДД)"},
            status=400,
        )

    if end_date < start_date:
        return JsonResponse(
            {"error": "Дата окончания не может быть раньше даты начала"},
            status=400,
        )

    days_requested = (end_date - start_date).days + 1

    # Берём остаток по году начала отпуска
    year = start_date.year
    balance, _ = VacationBalance.objects.get_or_create(
        user=request.user,
        year=year,
        defaults={"days_remaining": 0},
    )

    initial_days = balance.days_remaining
    planned_days = _calculate_planned_days(request.user, year)
    available = max(initial_days - planned_days, 0)

    if days_requested > available:
        return JsonResponse(
            {
                "error": f"У вас нет доступных дней отпуска для выбранного периода на {year} год.",
                "days_requested": days_requested,
                "available_days": available,
            },
            status=400,
        )

    req = VacationRequest.objects.create(
        user=request.user,
        start_date=start_date,
        end_date=end_date,
        status="pending",
        confirmed_by_employee=False,
    )

    data = {
        "id": req.id,
        "start_date": str(req.start_date),
        "end_date": str(req.end_date),
        "status": req.status,
        "confirmed_by_employee": req.confirmed_by_employee,
    }

    return JsonResponse(data, status=201)
