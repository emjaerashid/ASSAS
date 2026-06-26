from rest_framework import serializers
from core.models import (
    User, Programme, Student, Subject, Prerequisite,
    Enrolment, ExceptionLog, Rule, AddDropRequest, Timetable,
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'student_id', 'full_name', 'role', 'is_active', 'date_joined']


class ProgrammeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Programme
        fields = '__all__'


class SubjectSerializer(serializers.ModelSerializer):
    prerequisites = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = ['subject_code', 'subject_name', 'credit_hours', 'programme', 'year', 'semester', 'prerequisites']

    def get_prerequisites(self, obj):
        return [
            {
                'subject_code': p.prerequisite_subject.subject_code,
                'subject_name': p.prerequisite_subject.subject_name,
            }
            for p in obj.prerequisites.select_related('prerequisite_subject').all()
        ]


class StudentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    programme = ProgrammeSerializer(read_only=True)

    class Meta:
        model = Student
        fields = [
            'id', 'user', 'programme', 'current_year', 'current_semester',
            'status', 'total_credits_earned', 'cgpa', 'is_repeat', 'is_transfer',
            'effective_credit_cap',
        ]


class EnrolmentSerializer(serializers.ModelSerializer):
    subject = SubjectSerializer(read_only=True)
    student_id_display = serializers.CharField(source='student.user.student_id', read_only=True)
    student_name = serializers.CharField(source='student.user.full_name', read_only=True)

    class Meta:
        model = Enrolment
        fields = [
            'id', 'student', 'student_id_display', 'student_name',
            'subject', 'semester', 'status', 'grade', 'is_repeat', 'assigned_at',
        ]


class ExceptionLogSerializer(serializers.ModelSerializer):
    subject = SubjectSerializer(read_only=True)
    student_id_display = serializers.CharField(source='student.user.student_id', read_only=True)
    student_name = serializers.CharField(source='student.user.full_name', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.full_name', read_only=True, default=None)

    class Meta:
        model = ExceptionLog
        fields = [
            'id', 'student', 'student_id_display', 'student_name',
            'subject', 'reason', 'details', 'status',
            'reviewed_by', 'reviewed_by_name', 'reviewed_at', 'created_at',
        ]


class RuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rule
        fields = '__all__'


class AddDropRequestSerializer(serializers.ModelSerializer):
    subject = SubjectSerializer(read_only=True)
    student_id_display = serializers.CharField(source='student.user.student_id', read_only=True)
    student_name = serializers.CharField(source='student.user.full_name', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.full_name', read_only=True, default=None)
    subject_code = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = AddDropRequest
        fields = [
            'id', 'student', 'student_id_display', 'student_name',
            'subject', 'subject_code', 'action', 'reason', 'status',
            'semester', 'reviewed_by', 'reviewed_by_name', 'reviewed_at',
            'admin_remarks', 'created_at',
        ]
        read_only_fields = ['student', 'status', 'reviewed_by', 'reviewed_at', 'admin_remarks']


class TimetableSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.full_name', read_only=True, default=None)

    class Meta:
        model = Timetable
        fields = [
            'id', 'title', 'programme', 'semester', 'file',
            'uploaded_by', 'uploaded_by_name', 'uploaded_at',
        ]
        read_only_fields = ['uploaded_by']


class LoginSerializer(serializers.Serializer):
    student_id = serializers.CharField()
    ic_passport = serializers.CharField()


class CreateStudentSerializer(serializers.Serializer):
    student_id = serializers.CharField(max_length=20)
    full_name = serializers.CharField(max_length=200)
    ic_passport = serializers.CharField(max_length=50)
    programme_code = serializers.CharField(max_length=20)
    current_year = serializers.IntegerField(default=1)
    current_semester = serializers.IntegerField(default=1)
    status = serializers.ChoiceField(choices=Student.STATUS_CHOICES, default='active')
    is_repeat = serializers.BooleanField(default=False)
    is_transfer = serializers.BooleanField(default=False)
