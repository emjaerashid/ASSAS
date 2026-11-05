from rest_framework import serializers
from core.models import (
    User, Faculty, Programme, Student, Subject, Prerequisite,
    Enrolment, ExceptionLog, Rule, AddDropRequest, Timetable, TimeSlot, Venue,
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'student_id', 'full_name', 'ic_passport', 'role', 'is_active', 'date_joined']


class FacultySerializer(serializers.ModelSerializer):
    class Meta:
        model = Faculty
        fields = '__all__'


class VenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Venue
        fields = ['name', 'capacity']


class ProgrammeSerializer(serializers.ModelSerializer):
    faculty_name = serializers.CharField(source='faculty.faculty_name', read_only=True, default=None)

    class Meta:
        model = Programme
        fields = '__all__'


class SubjectSerializer(serializers.ModelSerializer):
    prerequisites = serializers.SerializerMethodField()
    prerequisite_codes = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )
    programmes = serializers.SerializerMethodField()
    programme_codes = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )

    class Meta:
        model = Subject
        fields = [
            'subject_code', 'subject_name', 'credit_hours', 'programmes', 'programme_codes', 'semester',
            'prerequisites', 'prerequisite_codes',
        ]

    def get_prerequisites(self, obj):
        return [
            {
                'subject_code': p.prerequisite_subject.subject_code,
                'subject_name': p.prerequisite_subject.subject_name,
            }
            for p in obj.prerequisites.select_related('prerequisite_subject').all()
        ]

    def get_programmes(self, obj):
        return [
            {'programme_code': p.programme_code, 'programme_name': p.programme_name}
            for p in obj.programmes.all()
        ]

    def create(self, validated_data):
        prerequisite_codes = validated_data.pop('prerequisite_codes', [])
        programme_codes = validated_data.pop('programme_codes', [])
        subject = Subject.objects.create(**validated_data)
        self._set_programmes(subject, programme_codes)
        self._set_prerequisites(subject, prerequisite_codes)
        return subject

    def update(self, instance, validated_data):
        prerequisite_codes = validated_data.pop('prerequisite_codes', None)
        programme_codes = validated_data.pop('programme_codes', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if programme_codes is not None:
            self._set_programmes(instance, programme_codes)
        if prerequisite_codes is not None:
            self._set_prerequisites(instance, prerequisite_codes)
        return instance

    def _set_programmes(self, subject, codes):
        subject.programmes.set(Programme.objects.filter(programme_code__in=codes))

    def _set_prerequisites(self, subject, codes):
        subject.prerequisites.all().delete()
        for code in codes:
            if code == subject.subject_code:
                continue
            try:
                prerequisite_subject = Subject.objects.get(subject_code=code)
            except Subject.DoesNotExist:
                continue
            Prerequisite.objects.create(subject=subject, prerequisite_subject=prerequisite_subject)


class StudentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    programme = ProgrammeSerializer(read_only=True)

    class Meta:
        model = Student
        fields = [
            'id', 'user', 'programme', 'photo', 'current_semester',
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
    student_semester = serializers.IntegerField(source='student.current_semester', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.full_name', read_only=True, default=None)

    class Meta:
        model = ExceptionLog
        fields = [
            'id', 'student', 'student_id_display', 'student_name', 'student_semester',
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


class TimeSlotSerializer(serializers.ModelSerializer):
    subject_code = serializers.CharField(source='subject.subject_code', read_only=True)
    subject_name = serializers.CharField(source='subject.subject_name', read_only=True)
    subject_semester = serializers.IntegerField(source='subject.semester', read_only=True)

    class Meta:
        model = TimeSlot
        fields = [
            'id', 'timetable', 'subject', 'subject_code', 'subject_name', 'subject_semester',
            'day_of_week', 'start_time', 'end_time', 'venue',
        ]
        read_only_fields = ['timetable']


class TimetableSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.full_name', read_only=True, default=None)
    time_slots = TimeSlotSerializer(many=True, read_only=True)
    programmes = serializers.SerializerMethodField()
    programme_codes = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )

    class Meta:
        model = Timetable
        fields = [
            'id', 'title', 'programmes', 'programme_codes', 'semester', 'file',
            'uploaded_by', 'uploaded_by_name', 'uploaded_at', 'time_slots',
        ]
        read_only_fields = ['uploaded_by']

    def get_programmes(self, obj):
        return [
            {'programme_code': p.programme_code, 'programme_name': p.programme_name}
            for p in obj.programmes.all()
        ]

    def create(self, validated_data):
        programme_codes = validated_data.pop('programme_codes', [])
        timetable = Timetable.objects.create(**validated_data)
        self._set_programmes(timetable, programme_codes)
        return timetable

    def update(self, instance, validated_data):
        programme_codes = validated_data.pop('programme_codes', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if programme_codes is not None:
            self._set_programmes(instance, programme_codes)
        return instance

    def _set_programmes(self, timetable, codes):
        timetable.programmes.set(Programme.objects.filter(programme_code__in=codes))


class LoginSerializer(serializers.Serializer):
    student_id = serializers.CharField()
    ic_passport = serializers.CharField()


class CreateStudentSerializer(serializers.Serializer):
    semester_intake = serializers.RegexField(r'^\d{6}$', error_messages={
        'invalid': 'Semester intake must be 6 digits, e.g. 202401.',
    })
    intake_day = serializers.RegexField(r'^\d{2}$', error_messages={
        'invalid': 'Intake day must be 2 digits, e.g. 02.',
    })
    full_name = serializers.CharField(max_length=200)
    ic_passport = serializers.CharField(max_length=50)
    programme_code = serializers.CharField(max_length=20)
    photo = serializers.ImageField(required=False, allow_null=True)
    current_semester = serializers.IntegerField(default=1)
    status = serializers.ChoiceField(choices=Student.STATUS_CHOICES, default='active')
    is_repeat = serializers.BooleanField(default=False)
    is_transfer = serializers.BooleanField(default=False)
