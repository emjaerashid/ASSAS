from decimal import Decimal, ROUND_HALF_UP

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

GRADE_POINTS = {
    'A': Decimal('4.00'), 'A-': Decimal('3.67'),
    'B+': Decimal('3.33'), 'B': Decimal('3.00'), 'B-': Decimal('2.67'),
    'C+': Decimal('2.33'), 'C': Decimal('2.00'), 'C-': Decimal('1.67'),
    'D+': Decimal('1.33'), 'D': Decimal('1.00'),
    'F': Decimal('0.00'),
}


class UserManager(BaseUserManager):
    def create_user(self, student_id, password=None, **extra_fields):
        if not student_id:
            raise ValueError('Student ID is required')
        user = self.model(student_id=student_id, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, student_id, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        return self.create_user(student_id, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('admin', 'Administrator'),
    ]

    student_id = models.CharField(max_length=20, unique=True)
    full_name = models.CharField(max_length=200)
    ic_passport = models.CharField(max_length=50, verbose_name='IC/Passport Number')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = 'student_id'
    REQUIRED_FIELDS = ['full_name']

    def __str__(self):
        return f"{self.student_id} - {self.full_name}"


class Faculty(models.Model):
    faculty_code = models.CharField(max_length=20, primary_key=True)
    faculty_name = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.faculty_code} - {self.faculty_name}"


class Programme(models.Model):
    programme_code = models.CharField(max_length=20, primary_key=True)
    programme_name = models.CharField(max_length=200)
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE, related_name='programmes', null=True, blank=True)
    total_credits = models.IntegerField(default=120)
    max_credits_per_sem = models.IntegerField(default=21)
    probation_credit_cap = models.IntegerField(default=12)
    total_semesters = models.IntegerField(default=8)

    def __str__(self):
        return f"{self.programme_code} - {self.programme_name}"


class Student(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('probation', 'On Probation'),
        ('graduated', 'Graduated'),
        ('suspended', 'Suspended'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    programme = models.ForeignKey(Programme, on_delete=models.CASCADE, related_name='students')
    current_year = models.IntegerField(default=1)
    current_semester = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    total_credits_earned = models.IntegerField(default=0)
    cgpa = models.DecimalField(max_digits=4, decimal_places=2, default=0.00)
    is_repeat = models.BooleanField(default=False)
    is_transfer = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.student_id} - {self.user.full_name}"

    @property
    def effective_credit_cap(self):
        if self.status == 'probation':
            return self.programme.probation_credit_cap
        return self.programme.max_credits_per_sem

    def recompute_total_credits_earned(self):
        """Recalculate total_credits_earned from passed enrolments and persist it.

        Skipped for transfer students, whose earned credits may include
        externally-verified transfer credit not represented by local
        Enrolment records (see the 'transfer_credit' exception review flow).
        """
        if self.is_transfer:
            return self.total_credits_earned

        passed = self.enrolments.filter(status='passed').select_related('subject')
        total = sum(e.subject.credit_hours for e in passed)
        if total != self.total_credits_earned:
            self.total_credits_earned = total
            self.save(update_fields=['total_credits_earned'])
        return self.total_credits_earned

    def recompute_cgpa(self):
        """Recalculate CGPA from graded enrolments (passed or failed) and persist it.

        Weighted by credit hours across every graded attempt, same as
        total_credits_earned; skipped for transfer students for the same reason.
        """
        if self.is_transfer:
            return self.cgpa

        graded = self.enrolments.filter(
            status__in=['passed', 'failed'],
        ).exclude(grade__isnull=True).exclude(grade='').select_related('subject')

        total_points = Decimal('0')
        total_credits = 0
        for e in graded:
            point = GRADE_POINTS.get(e.grade)
            if point is None:
                continue
            total_points += point * e.subject.credit_hours
            total_credits += e.subject.credit_hours

        new_cgpa = (
            (total_points / total_credits).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            if total_credits else Decimal('0.00')
        )
        if new_cgpa != self.cgpa:
            self.cgpa = new_cgpa
            self.save(update_fields=['cgpa'])
        return self.cgpa


class Subject(models.Model):
    subject_code = models.CharField(max_length=20, primary_key=True)
    subject_name = models.CharField(max_length=200)
    credit_hours = models.IntegerField(default=3)
    programme = models.ForeignKey(Programme, on_delete=models.CASCADE, related_name='subjects')
    year = models.IntegerField()
    semester = models.IntegerField()

    class Meta:
        ordering = ['year', 'semester', 'subject_code']

    def __str__(self):
        return f"{self.subject_code} - {self.subject_name}"


class Prerequisite(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='prerequisites')
    prerequisite_subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='is_prerequisite_for')

    class Meta:
        unique_together = ('subject', 'prerequisite_subject')

    def __str__(self):
        return f"{self.subject.subject_code} requires {self.prerequisite_subject.subject_code}"


class Enrolment(models.Model):
    STATUS_CHOICES = [
        ('assigned', 'Assigned'),
        ('passed', 'Passed'),
        ('failed', 'Failed'),
        ('dropped', 'Dropped'),
        ('in_progress', 'In Progress'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='enrolments')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='enrolments')
    semester = models.CharField(max_length=10, help_text='e.g. 202601')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='assigned')
    grade = models.CharField(max_length=5, blank=True, null=True)
    is_repeat = models.BooleanField(default=False)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-assigned_at']

    def __str__(self):
        return f"{self.student.user.student_id} - {self.subject.subject_code} ({self.status})"


class ExceptionLog(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    REASON_CHOICES = [
        ('prerequisite_unmet', 'Prerequisite Not Met'),
        ('credit_limit_exceeded', 'Credit Limit Exceeded'),
        ('subject_limit_exceeded', 'Subject Count Limit Exceeded'),
        ('repeat_subject', 'Repeat Subject'),
        ('probation_cap', 'Probation Credit Cap'),
        ('conflict', 'Schedule Conflict'),
        ('transfer_credit', 'Transfer Credit Review'),
        ('other', 'Other'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='exception_logs')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='exception_logs')
    enrolment = models.ForeignKey(Enrolment, on_delete=models.CASCADE, related_name='exception_logs', null=True, blank=True)
    reason = models.CharField(max_length=30, choices=REASON_CHOICES)
    details = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_exceptions')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.user.student_id} - {self.subject.subject_code} - {self.reason}"


class Rule(models.Model):
    RULE_TYPES = [
        ('max_credits', 'Maximum Credits Per Semester'),
        ('probation_cap', 'Probation Credit Cap'),
        ('min_credits', 'Minimum Credits Per Semester'),
        ('max_repeat', 'Maximum Repeat Attempts'),
    ]

    rule_type = models.CharField(max_length=30, choices=RULE_TYPES)
    rule_value = models.IntegerField()
    programme = models.ForeignKey(Programme, on_delete=models.CASCADE, related_name='rules', null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.rule_type}: {self.rule_value}"


class AddDropRequest(models.Model):
    ACTION_CHOICES = [
        ('add', 'Add Subject'),
        ('drop', 'Drop Subject'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='add_drop_requests')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='add_drop_requests')
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    semester = models.CharField(max_length=10)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_requests')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    admin_remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.user.student_id} - {self.action} {self.subject.subject_code}"


class Timetable(models.Model):
    title = models.CharField(max_length=200)
    programme = models.ForeignKey(Programme, on_delete=models.CASCADE, related_name='timetables')
    semester = models.CharField(max_length=10)
    file = models.FileField(upload_to='timetables/')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='uploaded_timetables')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.title} - {self.semester}"
