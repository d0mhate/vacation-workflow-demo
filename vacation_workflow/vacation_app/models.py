from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Roles(models.TextChoices):
        EMPLOYEE = 'employee', 'Employee'
        MANAGER = 'manager', 'Manager'
        HR = 'hr', 'HR'

    role = models.CharField(max_length=20, choices=Roles.choices, default=Roles.EMPLOYEE)
    manager = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='team_members')

    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)

    def __str__(self):
        return f"{self.username} ({self.role})"




class VacationRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vacation_requests')
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_by_employee = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} {self.start_date} - {self.end_date} ({self.status})"


class VacationSchedule(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vacation_schedules')
    year = models.PositiveIntegerField()
    period_from = models.DateField()
    period_to = models.DateField()

    def __str__(self):
        return f"{self.user.username} schedule {self.year}"


class Notification(models.Model):
    class Type(models.TextChoices):
        REQUEST_APPROVED = 'request_approved', 'Request Approved'
        REQUEST_REJECTED = 'request_rejected', 'Request Rejected'
        REQUEST_CREATED = 'request_created', 'Request Created'
        REMINDER_UPCOMING = 'reminder_upcoming', 'Upcoming Vacation Reminder'
        REQUEST_RESCHEDULED = 'request_rescheduled', 'Request Rescheduled'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(
        max_length=50,
        choices=Type.choices,
        default=Type.REQUEST_CREATED,
    )
    request = models.ForeignKey(VacationRequest, null=True, blank=True, on_delete=models.CASCADE)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.user.username}: {self.type}"

class VacationBalance(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='vacation_balances'
    )
    year = models.IntegerField(default=2025)
    days_remaining = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('user', 'year')
        ordering = ['-year']

    def __str__(self):
        return f'{self.user.username} — {self.year}: {self.days_remaining} дн.'
