from django.core.management.base import BaseCommand
from django.db import transaction

from vacation_app.models import User, VacationBalance

import random


class Command(BaseCommand):
    help = (
        "Create demo users for each role (employee, manager, hr) with the default "
        "password 'password123' and preset vacation balances."
    )

    FIRST_NAMES = ["Иван", "Петр", "Алексей", "Дмитрий", "Сергей", "Михаил", "Анна", "Екатерина", "Ольга", "Мария"]
    LAST_NAMES = ["Иванов", "Петров", "Сидоров", "Кузнецов", "Смирнов", "Васильев", "Козлова", "Соколова", "Попова", "Орлова"]

    def random_full_name(self):
        return f"{random.choice(self.FIRST_NAMES)} {random.choice(self.LAST_NAMES)}"

    def handle(self, *args, **options):
        with transaction.atomic():
            self.stdout.write(self.style.MIGRATE_HEADING("Creating demo roles..."))

            manager, _ = User.objects.get_or_create(
                username="manager",
                defaults={
                    "role": User.Roles.MANAGER,
                    "first_name": random.choice(self.FIRST_NAMES),
                    "last_name": random.choice(self.LAST_NAMES),
                },
            )
            manager.set_password("password123")
            manager.save()
            self.stdout.write(self.style.SUCCESS("Manager user ready: manager/password123"))

            employee, _ = User.objects.get_or_create(
                username="employee",
                defaults={
                    "role": User.Roles.EMPLOYEE,
                    "first_name": random.choice(self.FIRST_NAMES),
                    "last_name": random.choice(self.LAST_NAMES),
                },
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
                defaults={
                    "role": User.Roles.HR,
                    "first_name": random.choice(self.FIRST_NAMES),
                    "last_name": random.choice(self.LAST_NAMES),
                },
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
