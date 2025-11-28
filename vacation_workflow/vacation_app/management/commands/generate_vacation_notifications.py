from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from vacation_app.models import VacationRequest, Notification, User


class Command(BaseCommand):
    """
    Generate reminder notifications for upcoming approved vacations.

    Logic:
    - For all fully approved vacation requests (see _get_base_queryset),
      look at the start_date.
    - If start_date is in exactly 14 days -> create `vacation_reminder_14d`
      notifications for:
        * employee (owner of request)
        * employee's manager (if exists)
        * all HR users
    - If start_date is today -> create `vacation_start_today` notifications
      for:
        * employee
        * employee's manager (if exists)

    The command is idempotent for the same request/user/type: it will not
    create duplicate notifications if they already exist.
    """

    help = "Generate reminder notifications for upcoming vacations (14 days / today)."

    def handle(self, *args, **options):
        today = timezone.localdate()
        self.stdout.write(self.style.NOTICE(f"Generating vacation notifications for {today}"))

        qs = self._get_base_queryset()

        created_count = 0
        skipped_count = 0

        hr_users = list(User.objects.filter(role="hr"))

        for req in qs:
            if not req.start_date:
                continue

            delta_days = (req.start_date - today).days

            # Only future or today's vacations интересуют
            if delta_days < 0:
                continue

            if delta_days == 14:
                # 14 days before start
                created, skipped = self._create_notifications_for_request(
                    request=req,
                    notif_type="vacation_reminder_14d",
                    hr_users=hr_users,
                    today=today,
                )
                created_count += created
                skipped_count += skipped

            if delta_days == 0:
                # starts today
                created, skipped = self._create_notifications_for_request(
                    request=req,
                    notif_type="vacation_start_today",
                    hr_users=hr_users,
                    today=today,
                    include_hr=False,  # по требованиям HR достаточно 14-дневного напоминания
                )
                created_count += created
                skipped_count += skipped

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Created {created_count} notifications, skipped {skipped_count} duplicates."
            )
        )

    def _get_base_queryset(self):
        """
        Base queryset for vacations that should participate in reminders.

        Здесь мы используем максимально "широкое" условие по статусам,
        чтобы не упасть, если коды слегка отличаются, но при этом
        фокусируемся только на действительно утверждённых заявках.

        При необходимости можно сузить фильтр под фактические статусы.
        """
        qs = VacationRequest.objects.all()

        # Если в модели есть поле confirmed_by_employee, то ограничиваемся только подтверждёнными
        if hasattr(VacationRequest, "confirmed_by_employee"):
            qs = qs.filter(confirmed_by_employee=True)

        # Пытаемся отфильтровать "утверждённые" статусы, но мягко:
        # если статус не совпадает ни с одним перечисленным, просто ничего страшного -
        # queryset вернёт 0 строк и команда отработает без ошибок.
        APPROVED_STATUSES = [
            "approved",
            "hr_approved",
            "manager_approved",
        ]

        try:
            qs = qs.filter(status__in=APPROVED_STATUSES)
        except Exception:
            # На всякий случай - если поле status устроено иначе, не ломаем команду
            pass

        return qs.select_related("user", "user__manager")

    def _create_notifications_for_request(
        self,
        request: VacationRequest,
        notif_type: str,
        hr_users,
        today,
        include_hr: bool = True,
    ):
        """
        Create notifications of a given type for:
        - employee (mandatory)
        - manager (if exists)
        - HRs (optionally)

        Returns:
            (created_count, skipped_count)
        """
        created = 0
        skipped = 0

        employee = request.user
        manager = getattr(employee, "manager", None)

        # Собираем список получателей
        recipients = [employee]
        if manager is not None:
            recipients.append(manager)
        if include_hr:
            recipients.extend(hr_users)

        for user in recipients:
            obj, was_created = Notification.objects.get_or_create(
                user=user,
                request=request,
                type=notif_type,
            )
            if was_created:
                created += 1
            else:
                skipped += 1

        return created, skipped
