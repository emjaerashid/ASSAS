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
    path('admin/students/<str:student_id>/subjects/', views.student_subjects_detail, name='student-subjects-detail'),

    # Admin: Assignment Trigger
    path('admin/assign/', views.trigger_assignment, name='trigger-assignment'),

    # Admin: Exception Management
    path('admin/exceptions/', views.list_exceptions, name='list-exceptions'),
    path('admin/exceptions/<int:pk>/resolve/', views.resolve_exception, name='resolve-exception'),
    path('admin/exceptions/<int:pk>/undo/', views.undo_exception, name='undo-exception'),
    path('admin/exceptions/<int:pk>/replacement-options/', views.exception_replacement_options, name='exception-replacement-options'),
    path('admin/exceptions/<int:pk>/replace/', views.replace_exception_subject, name='replace-exception-subject'),

    # Admin: Add/Drop Request Management
    path('admin/add-drop-requests/', views.list_add_drop_requests, name='list-add-drop-requests'),
    path('admin/add-drop-requests/<int:pk>/resolve/', views.resolve_add_drop_request, name='resolve-add-drop-request'),
    path('admin/add-drop-requests/<int:pk>/undo/', views.undo_add_drop_request, name='undo-add-drop-request'),

    # Admin: Timetable Management
    path('admin/timetables/', views.timetable_manage, name='timetable-manage'),
    path('admin/timetables/<int:pk>/', views.timetable_detail, name='timetable-detail'),
    path('admin/timetables/<int:pk>/slots/', views.timetable_slots, name='timetable-slots'),
    path('admin/timetables/<int:pk>/slots/<int:slot_id>/', views.timetable_slot_detail, name='timetable-slot-detail'),

    # Admin: Rules
    path('admin/rules/', views.rules_manage, name='rules-manage'),

    # Admin: Subject Management
    path('admin/subjects/', views.subject_create, name='subject-create'),
    path('admin/subjects/<str:subject_code>/', views.subject_detail, name='subject-detail'),

    # Admin: Faculty and Programme Management
    path('admin/faculties/', views.faculty_list_create, name='faculty-list-create'),
    path('admin/faculties/<str:faculty_code>/', views.faculty_detail, name='faculty-detail'),

    # Admin: Venue Management
    path('admin/venues/', views.venue_list_create, name='venue-list-create'),
    path('admin/venues/<str:name>/', views.venue_detail, name='venue-detail'),
    path('admin/programmes/create/', views.create_programme, name='create-programme'),
    path('admin/programmes/<str:programme_code>/', views.programme_detail, name='programme-detail'),

    # Shared
    path('programmes/', views.list_programmes, name='list-programmes'),
    path('subjects/', views.list_subjects, name='list-subjects'),

    # Student Views
    path('student/subjects/', views.student_assigned_subjects, name='student-subjects'),
    path('student/progress/', views.student_progress, name='student-progress'),
    path('student/exceptions/', views.student_exceptions, name='student-exceptions'),
    path('student/add-drop/', views.student_submit_add_drop, name='student-add-drop'),
    path('student/add-drop/history/', views.student_add_drop_requests, name='student-add-drop-history'),
    path('student/add-drop/<int:pk>/', views.student_edit_add_drop_request, name='student-edit-add-drop'),
    path('student/add-drop/<int:pk>/withdraw/', views.student_withdraw_add_drop_request, name='student-withdraw-add-drop'),
    path('student/timetables/', views.student_timetables, name='student-timetables'),
    path('student/my-timetable/', views.student_my_timetable, name='student-my-timetable'),
]
