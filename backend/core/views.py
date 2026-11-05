from datetime import date

from django.contrib.auth import authenticate, login, logout
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser

from core.models import (
    User, Faculty, Programme, Student, Subject, Enrolment,
    ExceptionLog, Rule, AddDropRequest, Timetable, TimeSlot, Venue, validate_semester_code,
)
from core.serializers import (
    UserSerializer, FacultySerializer, ProgrammeSerializer, StudentSerializer, SubjectSerializer,
    EnrolmentSerializer, ExceptionLogSerializer, RuleSerializer,
    AddDropRequestSerializer, TimetableSerializer, TimeSlotSerializer, VenueSerializer,
    LoginSerializer, CreateStudentSerializer,
)
from core.rule_engine import run_assignment_for_student, run_assignment_for_all, find_clash_free_replacements


def _semester_code_error(code):
    """Returns an error message if code doesn't match <year><01|05|09>, else None."""
    try:
        validate_semester_code(code)
        return None
    except ValidationError as e:
        return e.messages[0]


# Semester periods are contiguous: Jan-Apr, May-Aug, Sep-Dec, so the end of
# one is the day before the next begins.
SEMESTER_BOUNDS_BY_MONTH = {
    '01': (1, 4, 30),
    '05': (5, 8, 31),
    '09': (9, 12, 31),
}


def _semester_bounds(code):
    """Returns (start_date, end_date) for a validated <year><01|05|09> code."""
    year = int(code[:4])
    start_month, end_month, end_day = SEMESTER_BOUNDS_BY_MONTH[code[4:6]]
    return date(year, start_month, 1), date(year, end_month, end_day)


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'


class IsStudent(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'student'


# ─── Authentication ───

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    user = authenticate(
        request,
        student_id=serializer.validated_data['student_id'],
        ic_passport=serializer.validated_data['ic_passport'],
    )

    if user is None:
        return Response(
            {'error': 'Invalid Student ID or IC/Passport number.'},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    login(request, user)

    data = UserSerializer(user).data
    if user.role == 'student' and hasattr(user, 'student_profile'):
        data['student_profile'] = StudentSerializer(user.student_profile).data

    return Response(data)


@api_view(['POST'])
def logout_view(request):
    logout(request)
    return Response({'message': 'Logged out successfully.'})


@api_view(['GET'])
def current_user_view(request):
    if not request.user.is_authenticated:
        return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)

    data = UserSerializer(request.user).data
    if request.user.role == 'student' and hasattr(request.user, 'student_profile'):
        data['student_profile'] = StudentSerializer(request.user.student_profile).data

    return Response(data)


# ─── Admin: Student Management ───

def _generate_student_id(semester_intake, intake_day):
    """Student IDs are <semester_intake><intake_day><4-digit sequence>, e.g.
    202401 + 02 + 0001 -> 202401020001. The sequence restarts at 0001 for
    each distinct intake/day combination."""
    prefix = f"{semester_intake}{intake_day}"
    last_id = (
        User.objects.filter(student_id__startswith=prefix, student_id__regex=rf'^{prefix}\d{{4}}$')
        .order_by('-student_id')
        .values_list('student_id', flat=True)
        .first()
    )
    next_seq = int(last_id[len(prefix):]) + 1 if last_id else 1
    return f"{prefix}{next_seq:04d}"


@api_view(['POST'])
@permission_classes([IsAdmin])
@parser_classes([MultiPartParser, FormParser])
def create_student(request):
    serializer = CreateStudentSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    try:
        programme = Programme.objects.get(programme_code=data['programme_code'])
    except Programme.DoesNotExist:
        return Response({'error': 'Programme not found.'}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        student_id = _generate_student_id(data['semester_intake'], data['intake_day'])
        user = User.objects.create_user(
            student_id=student_id,
            password=data['ic_passport'],
            full_name=data['full_name'],
            ic_passport=data['ic_passport'],
            role='student',
        )
        student = Student.objects.create(
            user=user,
            programme=programme,
            photo=data.get('photo'),
            current_semester=data.get('current_semester', 1),
            status=data.get('status', 'active'),
            is_repeat=data.get('is_repeat', False),
            is_transfer=data.get('is_transfer', False),
        )

    return Response(StudentSerializer(student).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAdmin])
def list_students(request):
    students = Student.objects.select_related('user', 'programme').all()

    programme_filter = request.query_params.get('programme')
    if programme_filter:
        students = students.filter(programme__programme_code=programme_filter)

    status_filter = request.query_params.get('status')
    if status_filter:
        students = students.filter(status=status_filter)

    students = list(students)
    for student in students:
        student.recompute_total_credits_earned()
        student.recompute_cgpa()

    serializer = StudentSerializer(students, many=True)
    return Response(serializer.data)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAdmin])
def student_detail(request, student_id):
    try:
        user = User.objects.get(student_id=student_id)
        student = user.student_profile
    except (User.DoesNotExist, Student.DoesNotExist):
        return Response({'error': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        student.recompute_total_credits_earned()
        student.recompute_cgpa()
        return Response(StudentSerializer(student).data)

    if request.method == 'DELETE':
        if student.photo:
            student.photo.delete(save=False)
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    programme_code = request.data.get('programme_code')
    if programme_code:
        try:
            student.programme = Programme.objects.get(programme_code=programme_code)
        except Programme.DoesNotExist:
            return Response({'error': 'Programme not found.'}, status=status.HTTP_404_NOT_FOUND)

    boolean_fields = {'is_repeat', 'is_transfer'}
    for field in ['current_semester', 'status', 'total_credits_earned', 'cgpa', 'is_repeat', 'is_transfer', 'photo']:
        if field in request.data:
            value = request.data[field]
            if field in boolean_fields and isinstance(value, str):
                value = value.strip().lower() in ('true', '1', 't')
            setattr(student, field, value)
    student.save()

    user_fields = {}
    if 'full_name' in request.data:
        user_fields['full_name'] = request.data['full_name']
    if 'ic_passport' in request.data:
        user_fields['ic_passport'] = request.data['ic_passport']
    if user_fields:
        # The edit form always resends ic_passport, so only an actual change
        # resets the password to the new IC/Passport - otherwise a routine
        # edit would silently undo a password the student chose themselves.
        ic_changed = 'ic_passport' in user_fields and user_fields['ic_passport'] != user.ic_passport
        for attr, value in user_fields.items():
            setattr(user, attr, value)
        update_fields = list(user_fields.keys())
        if ic_changed:
            user.set_password(user_fields['ic_passport'])
            update_fields.append('password')
        user.save(update_fields=update_fields)

    return Response(StudentSerializer(student).data)


@api_view(['GET'])
@permission_classes([IsAdmin])
def student_subjects_detail(request, student_id):
    try:
        user = User.objects.get(student_id=student_id)
        student = user.student_profile
    except (User.DoesNotExist, Student.DoesNotExist):
        return Response({'error': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)

    enrolments = Enrolment.objects.filter(student=student).select_related('subject').order_by('-semester')
    data = []
    for e in enrolments:
        item = EnrolmentSerializer(e).data
        slots = TimeSlot.objects.filter(
            subject=e.subject,
            timetable__programmes=student.programme,
            timetable__semester=e.semester,
        ).select_related('subject')
        item['time_slots'] = TimeSlotSerializer(slots, many=True).data
        data.append(item)
    return Response(data)


# ─── Admin: Trigger Assignment ───

SEMESTER_DURATION_MAX_SUBJECTS = {12: 3, 19: 7}
# Minimum subjects a student should end up with for a semester of this
# duration (12-week short semester, 19-week long semester). This is
# informational, not enforced by the rule engine itself - the engine only
# ever assigns subjects a student is actually eligible for (prerequisites
# met, no clash, within the credit cap), so a shortfall against this
# minimum surfaces as an 'underload' flag on the result for a coordinator
# to review, rather than blocking the run or force-assigning ineligible
# subjects.
SEMESTER_DURATION_MIN_SUBJECTS = {12: 3, 19: 5}


def _flag_underload(result, min_subjects):
    """Marks a run_assignment_for_student() result if it ended up below the
    minimum subject count for this semester's duration, for the frontend to
    surface as a warning."""
    result['min_subjects_required'] = min_subjects
    result['underload'] = len(result['assigned']) < min_subjects
    return result


@api_view(['POST'])
@permission_classes([IsAdmin])
def trigger_assignment(request):
    semester = request.data.get('semester')
    student_id = request.data.get('student_id')
    duration_weeks = request.data.get('duration_weeks')
    programme_code = request.data.get('programme_code')
    faculty_code = request.data.get('faculty_code')

    if not semester:
        return Response({'error': 'Semester is required.'}, status=status.HTTP_400_BAD_REQUEST)

    semester_error = _semester_code_error(semester)
    if semester_error:
        return Response({'error': semester_error}, status=status.HTTP_400_BAD_REQUEST)

    semester_start, _ = _semester_bounds(semester)
    today = timezone.localdate()
    if today < semester_start:
        return Response(
            {'error': (
                f"Cannot run assignment for semester {semester}: the current semester "
                f"has not ended yet (today is {today.isoformat()} MYT; {semester} starts {semester_start.isoformat()})."
            )},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Default to a long (19-week) semester - max 7 subjects - when the
    # caller doesn't specify a duration, rather than leaving assignment
    # uncapped. A long semester's cap always applies unless a short (12-week)
    # one is explicitly requested.
    if duration_weeks is None:
        duration_weeks = 19
    try:
        duration_weeks = int(duration_weeks)
    except (TypeError, ValueError):
        return Response({'error': 'duration_weeks must be 12 or 19.'}, status=status.HTTP_400_BAD_REQUEST)

    if duration_weeks not in SEMESTER_DURATION_MAX_SUBJECTS:
        return Response({'error': 'duration_weeks must be 12 or 19.'}, status=status.HTTP_400_BAD_REQUEST)

    max_subjects = SEMESTER_DURATION_MAX_SUBJECTS[duration_weeks]
    min_subjects = SEMESTER_DURATION_MIN_SUBJECTS[duration_weeks]

    if programme_code and not Programme.objects.filter(programme_code=programme_code).exists():
        return Response({'error': 'Programme not found.'}, status=status.HTTP_404_NOT_FOUND)

    if faculty_code and not Faculty.objects.filter(faculty_code=faculty_code).exists():
        return Response({'error': 'Faculty not found.'}, status=status.HTTP_404_NOT_FOUND)

    if student_id:
        try:
            user = User.objects.get(student_id=student_id)
            student = user.student_profile
        except (User.DoesNotExist, Student.DoesNotExist):
            return Response({'error': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)

        target_programmes = Programme.objects.filter(pk=student.programme_id)
    else:
        target_students = Student.objects.filter(status__in=['active', 'probation'])
        if programme_code:
            target_students = target_students.filter(programme__programme_code=programme_code)
        if faculty_code:
            target_students = target_students.filter(programme__faculty__faculty_code=faculty_code)
        target_programmes = Programme.objects.filter(
            pk__in=target_students.values_list('programme_id', flat=True).distinct()
        )

    programmes_missing_slots = [
        p.programme_code for p in target_programmes
        if not TimeSlot.objects.filter(timetable__programmes=p, timetable__semester=semester).exists()
    ]
    if programmes_missing_slots:
        return Response(
            {'error': (
                f"Assign timeslots to subjects first. No time slots have been registered for "
                f"semester {semester} for programme(s): {', '.join(programmes_missing_slots)}."
            )},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if student_id:
        result = run_assignment_for_student(student, semester, max_subjects=max_subjects)
        _flag_underload(result, min_subjects)
        return Response(result)
    else:
        results = run_assignment_for_all(
            semester, max_subjects=max_subjects, programme_code=programme_code, faculty_code=faculty_code,
        )
        for result in results:
            _flag_underload(result, min_subjects)
        return Response({
            'semester': semester,
            'total_students': len(results),
            'results': results,
        })


# ─── Admin: Exception Management ───

@api_view(['GET'])
@permission_classes([IsAdmin])
def list_exceptions(request):
    exceptions = ExceptionLog.objects.select_related(
        'student__user', 'subject', 'reviewed_by'
    ).all()

    status_filter = request.query_params.get('status')
    if status_filter:
        exceptions = exceptions.filter(status=status_filter)

    serializer = ExceptionLogSerializer(exceptions, many=True)
    return Response(serializer.data)


def _apply_exception_effects(exception, semester):
    enrolment = Enrolment.objects.create(
        student=exception.student,
        subject=exception.subject,
        semester=semester,
        status='assigned',
    )
    exception.enrolment = enrolment
    exception.save(update_fields=['enrolment'])


def _revert_exception_effects(exception):
    if exception.enrolment_id:
        enrolment = exception.enrolment
        # Null the FK and save before deleting the enrolment: it cascades
        # (on_delete=CASCADE) and would otherwise delete this ExceptionLog too.
        exception.enrolment = None
        exception.save(update_fields=['enrolment'])
        enrolment.delete()


def _clash_free_replacement_subjects(exception, semester):
    """Manual/admin-facing replacement candidates for a conflict exception:
    every clash-free option regardless of prerequisite entanglement or
    semester, since a human is choosing deliberately here. (The automatic
    in-engine replacement attempted first, in RuleEngine._handle_clash_loser,
    uses the same underlying search restricted to "safe" subjects only.)"""
    return find_clash_free_replacements(
        exception.student, exception.student.programme, semester, exception.subject_id,
    )


@api_view(['PUT'])
@permission_classes([IsAdmin])
def resolve_exception(request, pk):
    try:
        exception = ExceptionLog.objects.get(pk=pk)
    except ExceptionLog.DoesNotExist:
        return Response({'error': 'Exception not found.'}, status=status.HTTP_404_NOT_FOUND)

    new_status = request.data.get('status')
    if new_status not in ('approved', 'rejected'):
        return Response({'error': 'Status must be approved or rejected.'}, status=status.HTTP_400_BAD_REQUEST)

    if new_status == 'approved' and exception.status != 'approved':
        semester_error = _semester_code_error(request.data.get('semester', ''))
        if semester_error:
            return Response({'error': semester_error}, status=status.HTTP_400_BAD_REQUEST)

    previous_status = exception.status
    if previous_status == 'approved' and new_status != 'approved':
        _revert_exception_effects(exception)

    exception.status = new_status
    exception.reviewed_by = request.user
    exception.reviewed_at = timezone.now()
    exception.save()

    if new_status == 'approved' and previous_status != 'approved':
        _apply_exception_effects(exception, request.data.get('semester', ''))

    return Response(ExceptionLogSerializer(exception).data)


@api_view(['POST'])
@permission_classes([IsAdmin])
def undo_exception(request, pk):
    try:
        exception = ExceptionLog.objects.get(pk=pk)
    except ExceptionLog.DoesNotExist:
        return Response({'error': 'Exception not found.'}, status=status.HTTP_404_NOT_FOUND)

    if exception.status == 'pending':
        return Response({'error': 'Exception is already pending.'}, status=status.HTTP_400_BAD_REQUEST)

    if exception.status == 'approved':
        _revert_exception_effects(exception)

    exception.status = 'pending'
    exception.reviewed_by = None
    exception.reviewed_at = None
    exception.save()

    return Response(ExceptionLogSerializer(exception).data)


@api_view(['GET'])
@permission_classes([IsAdmin])
def exception_replacement_options(request, pk):
    try:
        exception = ExceptionLog.objects.select_related('student__programme', 'subject').get(pk=pk)
    except ExceptionLog.DoesNotExist:
        return Response({'error': 'Exception not found.'}, status=status.HTTP_404_NOT_FOUND)

    if exception.reason != 'conflict':
        return Response(
            {'error': 'Replacement options are only available for scheduling-conflict exceptions.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    semester = request.query_params.get('semester', '')
    semester_error = _semester_code_error(semester)
    if semester_error:
        return Response({'error': semester_error}, status=status.HTTP_400_BAD_REQUEST)

    options = [
        {
            'subject_code': subject.subject_code,
            'subject_name': subject.subject_name,
            'semester': subject.semester,
            'credit_hours': subject.credit_hours,
            'time_slots': TimeSlotSerializer(slots, many=True).data,
        }
        for subject, slots in _clash_free_replacement_subjects(exception, semester)
    ]
    return Response(options)


@api_view(['POST'])
@permission_classes([IsAdmin])
def replace_exception_subject(request, pk):
    try:
        exception = ExceptionLog.objects.get(pk=pk)
    except ExceptionLog.DoesNotExist:
        return Response({'error': 'Exception not found.'}, status=status.HTTP_404_NOT_FOUND)

    if exception.reason != 'conflict':
        return Response(
            {'error': 'Only scheduling-conflict exceptions can be resolved with a replacement subject.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    semester = request.data.get('semester', '')
    semester_error = _semester_code_error(semester)
    if semester_error:
        return Response({'error': semester_error}, status=status.HTTP_400_BAD_REQUEST)

    subject_code = request.data.get('subject_code')
    if not subject_code:
        return Response({'error': 'subject_code is required.'}, status=status.HTTP_400_BAD_REQUEST)

    valid_subjects = {s.subject_code: s for s, _ in _clash_free_replacement_subjects(exception, semester)}
    if subject_code not in valid_subjects:
        return Response(
            {'error': 'That subject is not a valid clash-free replacement for this student and semester.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    replacement_subject = valid_subjects[subject_code]

    if exception.status == 'approved':
        _revert_exception_effects(exception)

    enrolment = Enrolment.objects.create(
        student=exception.student,
        subject=replacement_subject,
        semester=semester,
        status='assigned',
    )
    exception.enrolment = enrolment
    exception.status = 'approved'
    exception.reviewed_by = request.user
    exception.reviewed_at = timezone.now()
    replacement_note = (
        f"Resolved by substituting {replacement_subject.subject_code} "
        f"({replacement_subject.subject_name}) due to a scheduling conflict."
    )
    exception.details = f"{exception.details}\n{replacement_note}".strip()
    exception.save()

    return Response(ExceptionLogSerializer(exception).data)


# ─── Admin: Add/Drop Request Management ───

@api_view(['GET'])
@permission_classes([IsAdmin])
def list_add_drop_requests(request):
    requests_qs = AddDropRequest.objects.select_related(
        'student__user', 'subject', 'reviewed_by'
    ).all()

    status_filter = request.query_params.get('status')
    if status_filter:
        requests_qs = requests_qs.filter(status=status_filter)

    serializer = AddDropRequestSerializer(requests_qs, many=True)
    return Response(serializer.data)


def _apply_add_drop_effects(add_drop):
    if add_drop.action == 'add':
        Enrolment.objects.create(
            student=add_drop.student,
            subject=add_drop.subject,
            semester=add_drop.semester,
            status='assigned',
        )
    elif add_drop.action == 'drop':
        Enrolment.objects.filter(
            student=add_drop.student,
            subject=add_drop.subject,
            semester=add_drop.semester,
            status='assigned',
        ).update(status='dropped')


def _revert_add_drop_effects(add_drop):
    if add_drop.action == 'add':
        enrolment = Enrolment.objects.filter(
            student=add_drop.student,
            subject=add_drop.subject,
            semester=add_drop.semester,
            status='assigned',
        ).order_by('-assigned_at').first()
        if enrolment:
            enrolment.delete()
    elif add_drop.action == 'drop':
        Enrolment.objects.filter(
            student=add_drop.student,
            subject=add_drop.subject,
            semester=add_drop.semester,
            status='dropped',
        ).update(status='assigned')


@api_view(['PUT'])
@permission_classes([IsAdmin])
def resolve_add_drop_request(request, pk):
    try:
        add_drop = AddDropRequest.objects.get(pk=pk)
    except AddDropRequest.DoesNotExist:
        return Response({'error': 'Request not found.'}, status=status.HTTP_404_NOT_FOUND)

    new_status = request.data.get('status')
    if new_status not in ('approved', 'rejected'):
        return Response({'error': 'Status must be approved or rejected.'}, status=status.HTTP_400_BAD_REQUEST)

    previous_status = add_drop.status
    if previous_status == 'approved' and new_status != 'approved':
        _revert_add_drop_effects(add_drop)

    add_drop.status = new_status
    add_drop.reviewed_by = request.user
    add_drop.reviewed_at = timezone.now()
    add_drop.admin_remarks = request.data.get('admin_remarks', '')
    add_drop.save()

    if new_status == 'approved' and previous_status != 'approved':
        _apply_add_drop_effects(add_drop)

    return Response(AddDropRequestSerializer(add_drop).data)


@api_view(['POST'])
@permission_classes([IsAdmin])
def undo_add_drop_request(request, pk):
    try:
        add_drop = AddDropRequest.objects.get(pk=pk)
    except AddDropRequest.DoesNotExist:
        return Response({'error': 'Request not found.'}, status=status.HTTP_404_NOT_FOUND)

    if add_drop.status == 'pending':
        return Response({'error': 'Request is already pending.'}, status=status.HTTP_400_BAD_REQUEST)

    if add_drop.status == 'approved':
        _revert_add_drop_effects(add_drop)

    add_drop.status = 'pending'
    add_drop.reviewed_by = None
    add_drop.reviewed_at = None
    add_drop.admin_remarks = ''
    add_drop.save()

    return Response(AddDropRequestSerializer(add_drop).data)


# ─── Admin: Timetable Upload ───

@api_view(['GET', 'POST'])
@permission_classes([IsAdmin])
def timetable_manage(request):
    if request.method == 'GET':
        timetables = Timetable.objects.select_related('uploaded_by').prefetch_related('programmes', 'time_slots__subject').all()
        return Response(TimetableSerializer(timetables, many=True).data)

    if not request.data.get('programme_codes'):
        return Response({'error': 'At least one programme must be selected.'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = TimetableSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save(uploaded_by=request.user)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['PUT', 'DELETE'])
@permission_classes([IsAdmin])
def timetable_detail(request, pk):
    try:
        timetable = Timetable.objects.get(pk=pk)
    except Timetable.DoesNotExist:
        return Response({'error': 'Timetable not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'DELETE':
        timetable.file.delete()
        timetable.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    if 'programme_codes' in request.data and not request.data.get('programme_codes'):
        return Response({'error': 'At least one programme must be selected.'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = TimetableSerializer(timetable, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


# ─── Admin: Timetable Time Slots (clash detection) ───

def _find_clash(timetable, day_of_week, start_time, end_time, venue, exclude_pk=None):
    """Returns the first existing TimeSlot in this timetable that overlaps
    the given day/time/venue, or None. Same time in a different venue is fine."""
    candidate = TimeSlot(day_of_week=day_of_week, start_time=start_time, end_time=end_time, venue=venue)
    existing = TimeSlot.objects.filter(timetable=timetable, day_of_week=day_of_week).select_related('subject')
    if exclude_pk:
        existing = existing.exclude(pk=exclude_pk)
    for slot in existing:
        if candidate.overlaps(slot):
            return slot
    return None


@api_view(['GET', 'POST'])
@permission_classes([IsAdmin])
def timetable_slots(request, pk):
    try:
        timetable = Timetable.objects.get(pk=pk)
    except Timetable.DoesNotExist:
        return Response({'error': 'Timetable not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        slots = timetable.time_slots.select_related('subject').all()
        return Response(TimeSlotSerializer(slots, many=True).data)

    serializer = TimeSlotSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    if data['start_time'] >= data['end_time']:
        return Response({'error': 'start_time must be before end_time.'}, status=status.HTTP_400_BAD_REQUEST)

    clash = _find_clash(timetable, data['day_of_week'], data['start_time'], data['end_time'], data.get('venue', ''))
    if clash:
        venue_note = f" in {clash.venue}" if clash.venue else ''
        return Response(
            {'error': (
                f"Time clash: {clash.subject.subject_code} is already scheduled "
                f"{clash.get_day_of_week_display()} {clash.start_time.strftime('%H:%M')}-{clash.end_time.strftime('%H:%M')}{venue_note}. "
                f"Use a different venue to schedule another class at this time."
            )},
            status=status.HTTP_409_CONFLICT,
        )

    slot = TimeSlot.objects.create(timetable=timetable, **data)
    return Response(TimeSlotSerializer(slot).data, status=status.HTTP_201_CREATED)


@api_view(['PUT', 'DELETE'])
@permission_classes([IsAdmin])
def timetable_slot_detail(request, pk, slot_id):
    try:
        slot = TimeSlot.objects.get(pk=slot_id, timetable_id=pk)
    except TimeSlot.DoesNotExist:
        return Response({'error': 'Time slot not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'DELETE':
        slot.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = TimeSlotSerializer(slot, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    day_of_week = data.get('day_of_week', slot.day_of_week)
    start_time = data.get('start_time', slot.start_time)
    end_time = data.get('end_time', slot.end_time)
    venue = data.get('venue', slot.venue)

    if start_time >= end_time:
        return Response({'error': 'start_time must be before end_time.'}, status=status.HTTP_400_BAD_REQUEST)

    clash = _find_clash(slot.timetable, day_of_week, start_time, end_time, venue, exclude_pk=slot.pk)
    if clash:
        venue_note = f" in {clash.venue}" if clash.venue else ''
        return Response(
            {'error': (
                f"Time clash: {clash.subject.subject_code} is already scheduled "
                f"{clash.get_day_of_week_display()} {clash.start_time.strftime('%H:%M')}-{clash.end_time.strftime('%H:%M')}{venue_note}. "
                f"Use a different venue to schedule another class at this time."
            )},
            status=status.HTTP_409_CONFLICT,
        )

    for attr, value in data.items():
        setattr(slot, attr, value)
    slot.save()
    return Response(TimeSlotSerializer(slot).data)


# ─── Admin: Faculty Management ───

@api_view(['GET', 'POST'])
@permission_classes([IsAdmin])
def faculty_list_create(request):
    if request.method == 'GET':
        faculties = Faculty.objects.all()
        return Response(FacultySerializer(faculties, many=True).data)

    faculty_code = request.data.get('faculty_code')
    faculty_name = request.data.get('faculty_name')

    if not faculty_code or not faculty_name:
        return Response({'error': 'faculty_code and faculty_name are required.'}, status=status.HTTP_400_BAD_REQUEST)

    if Faculty.objects.filter(faculty_code=faculty_code).exists():
        return Response({'error': 'Faculty code already exists.'}, status=status.HTTP_400_BAD_REQUEST)

    faculty = Faculty.objects.create(faculty_code=faculty_code, faculty_name=faculty_name)
    return Response(FacultySerializer(faculty).data, status=status.HTTP_201_CREATED)


@api_view(['PUT', 'DELETE'])
@permission_classes([IsAdmin])
def faculty_detail(request, faculty_code):
    try:
        faculty = Faculty.objects.get(faculty_code=faculty_code)
    except Faculty.DoesNotExist:
        return Response({'error': 'Faculty not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'DELETE':
        if Programme.objects.filter(faculty=faculty).exists():
            return Response(
                {'error': 'Cannot delete a faculty with existing programmes. Delete its programmes first.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        faculty.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    faculty_name = request.data.get('faculty_name')
    if not faculty_name:
        return Response({'error': 'faculty_name is required.'}, status=status.HTTP_400_BAD_REQUEST)

    faculty.faculty_name = faculty_name
    faculty.save()
    return Response(FacultySerializer(faculty).data)


# ─── Admin: Venue Management ───

@api_view(['GET', 'POST'])
@permission_classes([IsAdmin])
def venue_list_create(request):
    if request.method == 'GET':
        venues = Venue.objects.all().order_by('name')
        return Response(VenueSerializer(venues, many=True).data)

    name = request.data.get('name')
    capacity = request.data.get('capacity')

    if not name or capacity in (None, ''):
        return Response({'error': 'name and capacity are required.'}, status=status.HTTP_400_BAD_REQUEST)

    name = name.strip()
    if Venue.objects.filter(name__iexact=name).exists():
        return Response({'error': 'Venue already exists.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        capacity = int(capacity)
        if capacity <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return Response({'error': 'capacity must be a positive integer.'}, status=status.HTTP_400_BAD_REQUEST)

    venue = Venue.objects.create(name=name, capacity=capacity)
    return Response(VenueSerializer(venue).data, status=status.HTTP_201_CREATED)


@api_view(['PUT', 'DELETE'])
@permission_classes([IsAdmin])
def venue_detail(request, name):
    try:
        venue = Venue.objects.get(name=name)
    except Venue.DoesNotExist:
        return Response({'error': 'Venue not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'DELETE':
        venue.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    capacity = request.data.get('capacity')
    try:
        capacity = int(capacity)
        if capacity <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return Response({'error': 'capacity must be a positive integer.'}, status=status.HTTP_400_BAD_REQUEST)

    venue.capacity = capacity
    venue.save()
    return Response(VenueSerializer(venue).data)


# ─── Admin: Programme and Subject Management ───

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def list_programmes(request):
    programmes = Programme.objects.all()
    return Response(ProgrammeSerializer(programmes, many=True).data)


@api_view(['POST'])
@permission_classes([IsAdmin])
def create_programme(request):
    data = request.data
    programme_code = data.get('programme_code')
    programme_name = data.get('programme_name')
    faculty_code = data.get('faculty_code')

    if not programme_code or not programme_name or not faculty_code:
        return Response(
            {'error': 'programme_code, programme_name, and faculty_code are required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        faculty = Faculty.objects.get(faculty_code=faculty_code)
    except Faculty.DoesNotExist:
        return Response({'error': 'Faculty not found.'}, status=status.HTTP_404_NOT_FOUND)

    if Programme.objects.filter(programme_code=programme_code).exists():
        return Response({'error': 'Programme code already exists.'}, status=status.HTTP_400_BAD_REQUEST)

    programme = Programme.objects.create(
        programme_code=programme_code,
        programme_name=programme_name,
        faculty=faculty,
        total_credits=data.get('total_credits', 120),
        max_credits_per_sem=data.get('max_credits_per_sem', 21),
        probation_credit_cap=data.get('probation_credit_cap', 12),
        total_semesters=data.get('total_semesters', 9),
    )
    return Response(ProgrammeSerializer(programme).data, status=status.HTTP_201_CREATED)


@api_view(['PUT', 'DELETE'])
@permission_classes([IsAdmin])
def programme_detail(request, programme_code):
    try:
        programme = Programme.objects.get(programme_code=programme_code)
    except Programme.DoesNotExist:
        return Response({'error': 'Programme not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'DELETE':
        if Student.objects.filter(programme=programme).exists():
            return Response(
                {'error': 'Cannot delete a programme with enrolled students.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        programme.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    data = request.data
    faculty_code = data.get('faculty_code')
    if faculty_code:
        try:
            programme.faculty = Faculty.objects.get(faculty_code=faculty_code)
        except Faculty.DoesNotExist:
            return Response({'error': 'Faculty not found.'}, status=status.HTTP_404_NOT_FOUND)

    for field in ['programme_name', 'total_credits', 'max_credits_per_sem', 'probation_credit_cap', 'total_semesters']:
        if field in data:
            setattr(programme, field, data[field])
    programme.save()
    return Response(ProgrammeSerializer(programme).data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def list_subjects(request):
    subjects = Subject.objects.prefetch_related('programmes', 'prerequisites__prerequisite_subject').all()

    programme_filter = request.query_params.get('programme')
    if programme_filter:
        subjects = subjects.filter(programmes__programme_code=programme_filter)

    semester_filter = request.query_params.get('semester')
    if semester_filter:
        subjects = subjects.filter(semester=int(semester_filter))

    return Response(SubjectSerializer(subjects, many=True).data)


@api_view(['POST'])
@permission_classes([IsAdmin])
def subject_create(request):
    if Subject.objects.filter(subject_code=request.data.get('subject_code')).exists():
        return Response({'error': 'Subject code already exists.'}, status=status.HTTP_400_BAD_REQUEST)

    if not request.data.get('programme_codes'):
        return Response({'error': 'At least one programme must be selected.'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = SubjectSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['PUT', 'DELETE'])
@permission_classes([IsAdmin])
def subject_detail(request, subject_code):
    try:
        subject = Subject.objects.get(subject_code=subject_code)
    except Subject.DoesNotExist:
        return Response({'error': 'Subject not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'DELETE':
        subject.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    data = {k: v for k, v in request.data.items() if k != 'subject_code'}
    if 'programme_codes' in data and not data.get('programme_codes'):
        return Response({'error': 'At least one programme must be selected.'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = SubjectSerializer(subject, data=data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


# ─── Admin: Rules Management ───

@api_view(['GET', 'POST'])
@permission_classes([IsAdmin])
def rules_manage(request):
    if request.method == 'GET':
        rules = Rule.objects.all()
        return Response(RuleSerializer(rules, many=True).data)

    serializer = RuleSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=status.HTTP_201_CREATED)


# ─── Admin: Dashboard Stats ───

@api_view(['GET'])
@permission_classes([IsAdmin])
def admin_dashboard(request):
    return Response({
        'total_students': Student.objects.count(),
        'active_students': Student.objects.filter(status='active').count(),
        'probation_students': Student.objects.filter(status='probation').count(),
        'total_programmes': Programme.objects.count(),
        'total_subjects': Subject.objects.count(),
        'pending_exceptions': ExceptionLog.objects.filter(status='pending').count(),
        'pending_add_drop': AddDropRequest.objects.filter(status='pending').count(),
    })


# ─── Student Views ───

@api_view(['GET'])
@permission_classes([IsStudent])
def student_assigned_subjects(request):
    student = request.user.student_profile
    semester = request.query_params.get('semester')

    enrolments = Enrolment.objects.filter(student=student).select_related('subject')
    if semester:
        enrolments = enrolments.filter(semester=semester)

    return Response(EnrolmentSerializer(enrolments, many=True).data)


@api_view(['GET'])
@permission_classes([IsStudent])
def student_progress(request):
    student = request.user.student_profile
    completed = Enrolment.objects.filter(student=student, status='passed')
    total_earned = student.recompute_total_credits_earned()
    student.recompute_cgpa()

    all_subjects = Subject.objects.filter(programmes=student.programme).count()
    completed_count = completed.count()

    return Response({
        'student': StudentSerializer(student).data,
        'total_programme_subjects': all_subjects,
        'completed_subjects': completed_count,
        'total_credits_earned': total_earned,
        'total_credits_required': student.programme.total_credits,
        'progress_percentage': round((total_earned / student.programme.total_credits) * 100, 1) if student.programme.total_credits > 0 else 0,
    })


@api_view(['GET'])
@permission_classes([IsStudent])
def student_exceptions(request):
    student = request.user.student_profile
    exceptions = ExceptionLog.objects.filter(student=student).select_related('subject', 'reviewed_by')
    return Response(ExceptionLogSerializer(exceptions, many=True).data)


@api_view(['POST'])
@permission_classes([IsStudent])
def student_submit_add_drop(request):
    student = request.user.student_profile
    subject_code = request.data.get('subject_code')
    action = request.data.get('action')
    reason = request.data.get('reason', '')
    semester = request.data.get('semester', '')

    if not subject_code or not action:
        return Response({'error': 'subject_code and action are required.'}, status=status.HTTP_400_BAD_REQUEST)

    if action not in ('add', 'drop'):
        return Response({'error': 'action must be add or drop.'}, status=status.HTTP_400_BAD_REQUEST)

    semester_error = _semester_code_error(semester)
    if semester_error:
        return Response({'error': semester_error}, status=status.HTTP_400_BAD_REQUEST)

    if not Enrolment.objects.filter(student=student, semester=semester).exists():
        return Response(
            {'error': 'Student can not request add/drop subjects before admin has run an assigmnent'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        subject = Subject.objects.get(subject_code=subject_code)
    except Subject.DoesNotExist:
        return Response({'error': 'Subject not found.'}, status=status.HTTP_404_NOT_FOUND)

    add_drop = AddDropRequest.objects.create(
        student=student,
        subject=subject,
        action=action,
        reason=reason,
        semester=semester,
    )

    return Response(AddDropRequestSerializer(add_drop).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsStudent])
def student_add_drop_requests(request):
    student = request.user.student_profile
    requests_qs = AddDropRequest.objects.filter(student=student).select_related('subject', 'reviewed_by')
    return Response(AddDropRequestSerializer(requests_qs, many=True).data)


@api_view(['PUT'])
@permission_classes([IsStudent])
def student_edit_add_drop_request(request, pk):
    student = request.user.student_profile
    try:
        add_drop = AddDropRequest.objects.get(pk=pk, student=student)
    except AddDropRequest.DoesNotExist:
        return Response({'error': 'Request not found.'}, status=status.HTTP_404_NOT_FOUND)

    if add_drop.status != 'pending':
        return Response({'error': 'Only pending requests can be edited.'}, status=status.HTTP_400_BAD_REQUEST)

    subject_code = request.data.get('subject_code')
    action = request.data.get('action')
    reason = request.data.get('reason', '')
    semester = request.data.get('semester', '')

    if not subject_code or not action:
        return Response({'error': 'subject_code and action are required.'}, status=status.HTTP_400_BAD_REQUEST)

    if action not in ('add', 'drop'):
        return Response({'error': 'action must be add or drop.'}, status=status.HTTP_400_BAD_REQUEST)

    semester_error = _semester_code_error(semester)
    if semester_error:
        return Response({'error': semester_error}, status=status.HTTP_400_BAD_REQUEST)

    if not Enrolment.objects.filter(student=student, semester=semester).exists():
        return Response(
            {'error': 'Student can not request add/drop subjects before admin has run an assigmnent'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        subject = Subject.objects.get(subject_code=subject_code)
    except Subject.DoesNotExist:
        return Response({'error': 'Subject not found.'}, status=status.HTTP_404_NOT_FOUND)

    add_drop.subject = subject
    add_drop.action = action
    add_drop.reason = reason
    add_drop.semester = semester
    add_drop.save()

    return Response(AddDropRequestSerializer(add_drop).data)


@api_view(['POST'])
@permission_classes([IsStudent])
def student_withdraw_add_drop_request(request, pk):
    student = request.user.student_profile
    try:
        add_drop = AddDropRequest.objects.get(pk=pk, student=student)
    except AddDropRequest.DoesNotExist:
        return Response({'error': 'Request not found.'}, status=status.HTTP_404_NOT_FOUND)

    if add_drop.status != 'pending':
        return Response({'error': 'Only pending requests can be withdrawn.'}, status=status.HTTP_400_BAD_REQUEST)

    add_drop.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([IsStudent])
def student_timetables(request):
    student = request.user.student_profile
    timetables = Timetable.objects.filter(programmes=student.programme).select_related('uploaded_by').prefetch_related('programmes')
    return Response(TimetableSerializer(timetables, many=True).data)


@api_view(['GET'])
@permission_classes([IsStudent])
def student_my_timetable(request):
    """The student's own weekly timetable: the TimeSlots for the subjects
    they're currently assigned to, for one semester. Defaults to their most
    recent semester with assigned subjects; ?semester= overrides."""
    student = request.user.student_profile
    semester = request.query_params.get('semester')

    enrolments = Enrolment.objects.filter(student=student, status='assigned')
    if semester:
        enrolments = enrolments.filter(semester=semester)
    else:
        semester = enrolments.order_by('-semester').values_list('semester', flat=True).first()
        enrolments = enrolments.filter(semester=semester) if semester else enrolments.none()

    slots = TimeSlot.objects.filter(
        subject__in=enrolments.values_list('subject_id', flat=True),
        timetable__programmes=student.programme,
        timetable__semester=semester,
    ).select_related('subject').order_by('day_of_week', 'start_time') if semester else TimeSlot.objects.none()

    return Response({
        'semester': semester,
        'slots': TimeSlotSerializer(slots, many=True).data,
    })
