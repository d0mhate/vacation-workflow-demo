from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User, VacationBalance, VacationRequest, VacationSchedule, Notification


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        ('Vacation', {'fields': ('role', 'manager')}),
    )
    list_display = ('username', 'email', 'role', 'manager', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_superuser')


@admin.register(VacationBalance)
class VacationBalanceAdmin(admin.ModelAdmin):
    list_display = ('user', 'days_remaining')


@admin.register(VacationRequest)
class VacationRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'start_date', 'end_date', 'status', 'confirmed_by_employee', 'created_at')
    list_filter = ('status', 'confirmed_by_employee')
    search_fields = ('user__username',)


@admin.register(VacationSchedule)
class VacationScheduleAdmin(admin.ModelAdmin):
    list_display = ('user', 'year', 'period_from', 'period_to')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'is_read', 'created_at')
    list_filter = ('is_read',)
