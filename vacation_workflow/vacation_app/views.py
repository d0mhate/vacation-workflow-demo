import csv
import json

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.middleware import csrf
from django.views.decorators.http import require_GET, require_POST

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
    balance, _ = VacationBalance.objects.get_or_create(user=request.user, defaults={'days_remaining': 0})
    return JsonResponse({'days_remaining': balance.days_remaining})


@login_required
@require_GET
def my_requests(request):
    if request.user.role != ROLE_EMPLOYEE:
        return HttpResponseForbidden()
    requests = VacationRequest.objects.filter(user=request.user).order_by('-created_at')
    return JsonResponse({'requests': [_serialize_request(req) for req in requests]})


@login_required
@require_POST
def create_request(request):
    if request.user.role != ROLE_EMPLOYEE:
        return HttpResponseForbidden()
    data = _get_request_data(request)
    from datetime import date

    start_date_str = data.get('start_date')
    end_date_str = data.get('end_date')
    if not start_date_str or not end_date_str:
        return _json_error('start_date and end_date are required')

    try:
        start_date = date.fromisoformat(start_date_str)
        end_date = date.fromisoformat(end_date_str)
    except ValueError:
        return _json_error('Invalid date format. Expected YYYY-MM-DD')

    vacation_request = VacationRequest.objects.create(
        user=request.user,
        start_date=start_date,
        end_date=end_date,
        status=VacationRequest.Status.PENDING,
        confirmed_by_employee=False,
    )
    return JsonResponse({'request': _serialize_request(vacation_request)}, status=201)


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
    if notification.type == Notification.Type.REQUEST_APPROVED and notification.request:
        return f"Ваша заявка на отпуск №{notification.request.id} была согласована."
    if notification.type == Notification.Type.REQUEST_REJECTED and notification.request:
        return f"Ваша заявка на отпуск №{notification.request.id} была отклонена."
    if notification.type == Notification.Type.REQUEST_CREATED and notification.request:
        return f"Создана новая заявка на отпуск №{notification.request.id}."
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
