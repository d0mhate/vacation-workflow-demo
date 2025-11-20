from django.core.management.base import BaseCommand
from django.db import transaction

from vacation_app.models import User, VacationBalance


class Command(BaseCommand):
    help = (
        "Create demo users for each role (employee, manager, hr) with the default "
        "password 'password123'."
    )

    def handle(self, *args, **options):
        with transaction.atomic():
            self.stdout.write(self.style.MIGRATE_HEADING("Creating demo roles..."))

            manager, _ = User.objects.get_or_create(
                username="manager",
                defaults={"role": User.Roles.MANAGER},
            )
            manager.set_password("password123")
            manager.save()
            self.stdout.write(self.style.SUCCESS("Manager user ready: manager/password123"))

            employee, _ = User.objects.get_or_create(
                username="employee",
                defaults={"role": User.Roles.EMPLOYEE},
            )
            employee.manager = manager
            employee.set_password("password123")
            employee.save()
            self.stdout.write(
                self.style.SUCCESS(
                    "Employee user ready (manager assigned): employee/password123"
                )
            )

            hr, _ = User.objects.get_or_create(
                username="hr",
                defaults={"role": User.Roles.HR},
            )
            hr.set_password("password123")
            hr.save()
            self.stdout.write(self.style.SUCCESS("HR user ready: hr/password123"))

            for user in (employee, manager, hr):
                VacationBalance.objects.get_or_create(user=user, defaults={"days_remaining": 20})

        self.stdout.write(self.style.MIGRATE_LABEL("Demo users created or updated."))
