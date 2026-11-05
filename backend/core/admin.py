from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from core.models import (
    User, Faculty, Programme, Student, Subject, Prerequisite,
    Enrolment, ExceptionLog, Rule, AddDropRequest, Timetable, TimeSlot, Venue,
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('student_id', 'full_name', 'role', 'is_active')
    list_filter = ('role', 'is_active')
    search_fields = ('student_id', 'full_name')
    ordering = ('student_id',)
    fieldsets = (
        (None, {'fields': ('student_id', 'password')}),
        ('Personal Info', {'fields': ('full_name', 'ic_passport', 'role')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    )
    add_fieldsets = (
        (None, {'fields': ('student_id', 'full_name', 'ic_passport', 'role', 'password1', 'password2')}),
    )


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ('faculty_code', 'faculty_name')


@admin.register(Programme)
class ProgrammeAdmin(admin.ModelAdmin):
    list_display = ('programme_code', 'programme_name', 'faculty', 'total_credits', 'max_credits_per_sem')


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('user', 'programme', 'current_semester', 'status')
    list_filter = ('programme', 'status', 'current_semester')


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('subject_code', 'subject_name', 'credit_hours', 'programme_list', 'semester')
    list_filter = ('programmes', 'semester')
    filter_horizontal = ('programmes',)

    def programme_list(self, obj):
        return ', '.join(p.programme_code for p in obj.programmes.all())
    programme_list.short_description = 'Programmes'


@admin.register(Prerequisite)
class PrerequisiteAdmin(admin.ModelAdmin):
    list_display = ('subject', 'prerequisite_subject')


@admin.register(Enrolment)
class EnrolmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'semester', 'status', 'is_repeat')
    list_filter = ('status', 'semester', 'is_repeat')


@admin.register(ExceptionLog)
class ExceptionLogAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'reason', 'status', 'created_at')
    list_filter = ('reason', 'status')


@admin.register(Rule)
class RuleAdmin(admin.ModelAdmin):
    list_display = ('rule_type', 'rule_value', 'programme', 'is_active')


@admin.register(AddDropRequest)
class AddDropRequestAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'action', 'status', 'created_at')
    list_filter = ('action', 'status')


@admin.register(Timetable)
class TimetableAdmin(admin.ModelAdmin):
    list_display = ('title', 'programme_list', 'semester', 'uploaded_at')
    filter_horizontal = ('programmes',)

    def programme_list(self, obj):
        return ', '.join(p.programme_code for p in obj.programmes.all())
    programme_list.short_description = 'Programmes'


@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ('timetable', 'subject', 'day_of_week', 'start_time', 'end_time', 'venue')
    list_filter = ('day_of_week', 'timetable__programmes')


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ('name', 'capacity')
