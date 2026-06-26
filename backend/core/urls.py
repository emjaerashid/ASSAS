from django.urls import path
from core import views

urlpatterns = [
    # Auth
    path('auth/login/', views.login_view, name='login'),
    path('auth/logout/', views.logout_view, name='logout'),
    path('auth/me/', views.current_user_view, name='current-user'),

    # Admin: Dashboard
    path('admin/dashboard/', views.admin_dashboard, name='admin-dashboard'),

    # Admin: Student Management
    path('admin/students/', views.list_students, name='list-students'),
    path('admin/students/create/', views.create_student, name='create-student'),
    path('admin/students/<str:student_id>/', views.student_detail, name='student-detail'),

    # Admin: Assignment Trigger
    path('admin/assign/', views.trigger_assignment, name='trigger-assignment'),

    # Admin: Exception Management
    path('admin/exceptions/', views.list_exceptions, name='list-exceptions'),
    path('admin/exceptions/<int:pk>/resolve/', views.resolve_exception, name='resolve-exception'),

    # Admin: Add/Drop Request Management
    path('admin/add-drop-requests/', views.list_add_drop_requests, name='list-add-drop-requests'),
    path('admin/add-drop-requests/<int:pk>/resolve/', views.resolve_add_drop_request, name='resolve-add-drop-request'),

    # Admin: Timetable Management
    path('admin/timetables/', views.timetable_manage, name='timetable-manage'),
    path('admin/timetables/<int:pk>/', views.timetable_delete, name='timetable-delete'),

    # Admin: Rules
    path('admin/rules/', views.rules_manage, name='rules-manage'),

    # Shared
    path('programmes/', views.list_programmes, name='list-programmes'),
    path('subjects/', views.list_subjects, name='list-subjects'),

    # Student Views
    path('student/subjects/', views.student_assigned_subjects, name='student-subjects'),
    path('student/progress/', views.student_progress, name='student-progress'),
    path('student/exceptions/', views.student_exceptions, name='student-exceptions'),
    path('student/add-drop/', views.student_submit_add_drop, name='student-add-drop'),
    path('student/add-drop/history/', views.student_add_drop_requests, name='student-add-drop-history'),
    path('student/timetables/', views.student_timetables, name='student-timetables'),
]
