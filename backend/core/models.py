from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin


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


class Programme(models.Model):
    programme_code = models.CharField(max_length=20, primary_key=True)
    programme_name = models.CharField(max_length=200)
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
