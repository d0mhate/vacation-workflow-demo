from django.core.management.base import BaseCommand
from django.db import transaction

from vacation_app.models import User, VacationBalance


class Command(BaseCommand):
    help = (
        "Create demo users for each role (employee, manager, hr) with the default "
        "password 'password123' and preset vacation balances."
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

            for user, days in (
                (employee, 20),
                (manager, 25),
                (hr, 30),
            ):
                VacationBalance.objects.update_or_create(
                    user=user,
                    defaults={"days_remaining": days},
                )

            self.stdout.write("")
            self.stdout.write(self.style.MIGRATE_HEADING("Demo users created or updated"))
            self.stdout.write(self.style.SUCCESS("You can log in with these accounts:"))
            self.stdout.write("  • Employee:  login=employee   password=password123  (manager: manager)")
            self.stdout.write("  • Manager:   login=manager    password=password123")
            self.stdout.write("  • HR:        login=hr         password=password123")
