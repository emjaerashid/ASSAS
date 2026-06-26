from django.contrib.auth import authenticate, login, logout
from django.utils import timezone
from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser

from core.models import (
    User, Programme, Student, Subject, Enrolment,
    ExceptionLog, Rule, AddDropRequest, Timetable,
)
from core.serializers import (
    UserSerializer, ProgrammeSerializer, StudentSerializer, SubjectSerializer,
    EnrolmentSerializer, ExceptionLogSerializer, RuleSerializer,
    AddDropRequestSerializer, TimetableSerializer,
    LoginSerializer, CreateStudentSerializer,
)
from core.rule_engine import run_assignment_for_student, run_assignment_for_all


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

@api_view(['POST'])
@permission_classes([IsAdmin])
def create_student(request):
    serializer = CreateStudentSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    if User.objects.filter(student_id=data['student_id']).exists():
        return Response({'error': 'Student ID already exists.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        programme = Programme.objects.get(programme_code=data['programme_code'])
    except Programme.DoesNotExist:
        return Response({'error': 'Programme not found.'}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(
        student_id=data['student_id'],
        password=data['ic_passport'],
        full_name=data['full_name'],
        ic_passport=data['ic_passport'],
        role='student',
    )

    student = Student.objects.create(
        user=user,
        programme=programme,
        current_year=data.get('current_year', 1),
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

    serializer = StudentSerializer(students, many=True)
    return Response(serializer.data)


@api_view(['GET', 'PUT'])
@permission_classes([IsAdmin])
def student_detail(request, student_id):
    try:
        user = User.objects.get(student_id=student_id)
        student = user.student_profile
    except (User.DoesNotExist, Student.DoesNotExist):
        return Response({'error': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(StudentSerializer(student).data)

    for field in ['current_year', 'current_semester', 'status', 'total_credits_earned', 'cgpa', 'is_repeat', 'is_transfer']:
        if field in request.data:
            setattr(student, field, request.data[field])
    student.save()
    return Response(StudentSerializer(student).data)


# ─── Admin: Trigger Assignment ───

@api_view(['POST'])
@permission_classes([IsAdmin])
def trigger_assignment(request):
    semester = request.data.get('semester')
    student_id = request.data.get('student_id')

    if not semester:
        return Response({'error': 'Semester is required.'}, status=status.HTTP_400_BAD_REQUEST)

    if student_id:
        try:
            user = User.objects.get(student_id=student_id)
            student = user.student_profile
        except (User.DoesNotExist, Student.DoesNotExist):
            return Response({'error': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)

        result = run_assignment_for_student(student, semester)
        return Response(result)
    else:
        results = run_assignment_for_all(semester)
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

    exception.status = new_status
    exception.reviewed_by = request.user
    exception.reviewed_at = timezone.now()
    exception.save()

    if new_status == 'approved':
        Enrolment.objects.create(
            student=exception.student,
            subject=exception.subject,
            semester=request.data.get('semester', ''),
            status='assigned',
        )

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

    add_drop.status = new_status
    add_drop.reviewed_by = request.user
    add_drop.reviewed_at = timezone.now()
    add_drop.admin_remarks = request.data.get('admin_remarks', '')
    add_drop.save()

    if new_status == 'approved':
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

    return Response(AddDropRequestSerializer(add_drop).data)


# ─── Admin: Timetable Upload ───

@api_view(['GET', 'POST'])
@permission_classes([IsAdmin])
def timetable_manage(request):
    if request.method == 'GET':
        timetables = Timetable.objects.select_related('uploaded_by', 'programme').all()
        return Response(TimetableSerializer(timetables, many=True).data)

    parser_classes = (MultiPartParser, FormParser)
    serializer = TimetableSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save(uploaded_by=request.user)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([IsAdmin])
def timetable_delete(request, pk):
    try:
        timetable = Timetable.objects.get(pk=pk)
    except Timetable.DoesNotExist:
        return Response({'error': 'Timetable not found.'}, status=status.HTTP_404_NOT_FOUND)
    timetable.file.delete()
    timetable.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# ─── Admin: Programme and Subject Management ───

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def list_programmes(request):
    programmes = Programme.objects.all()
    return Response(ProgrammeSerializer(programmes, many=True).data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def list_subjects(request):
    subjects = Subject.objects.select_related('programme').prefetch_related('prerequisites__prerequisite_subject').all()

    programme_filter = request.query_params.get('programme')
    if programme_filter:
        subjects = subjects.filter(programme__programme_code=programme_filter)

    year_filter = request.query_params.get('year')
    if year_filter:
        subjects = subjects.filter(year=int(year_filter))

    semester_filter = request.query_params.get('semester')
    if semester_filter:
        subjects = subjects.filter(semester=int(semester_filter))

    return Response(SubjectSerializer(subjects, many=True).data)


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
    total_earned = sum(e.subject.credit_hours for e in completed.select_related('subject'))

    student.total_credits_earned = total_earned
    student.save(update_fields=['total_credits_earned'])

    all_subjects = Subject.objects.filter(programme=student.programme).count()
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


@api_view(['GET'])
@permission_classes([IsStudent])
def student_timetables(request):
    student = request.user.student_profile
    timetables = Timetable.objects.filter(programme=student.programme).select_related('uploaded_by')
    return Response(TimetableSerializer(timetables, many=True).data)
