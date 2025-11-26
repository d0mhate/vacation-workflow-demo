from django.urls import path

from . import views

urlpatterns = [
    path('login', views.login_view, name='login'),
    path('logout', views.logout_view, name='logout'),
    path('me', views.me, name='me'),
    path('vacation/balance', views.vacation_balance, name='vacation_balance'),
    path('vacation/requests/my', views.my_requests, name='my_requests'),
    path('vacation/request', views.create_request, name='create_request'),
    path('vacation/request/<int:pk>/update', views.update_request, name='update_request'),
    path('vacation/request/<int:pk>/confirm', views.confirm_request, name='confirm_request'),
    path('vacation/balances', views.vacation_balances, name='vacation_balances'),
    path('manager/requests', views.manager_requests, name='manager_requests'),
    path('manager/request/<int:pk>/approve', views.manager_approve, name='manager_approve'),
    path('manager/request/<int:pk>/reject', views.manager_reject, name='manager_reject'),
    path('hr/requests', views.hr_requests, name='hr_requests'),
    path('hr/export', views.hr_export, name='hr_export'),
    path('notifications', views.notifications_list, name='notifications_list'),
    path('notifications/unread_count', views.notifications_unread_count, name='notifications_unread_count'),
    path('notifications/<int:pk>/read', views.notification_mark_read, name='notification_mark_read'),
    path('profile/update', views.profile_update, name='profile_update'),
    path("hr/schedule", views.hr_schedule, name="hr_schedule"),
]
