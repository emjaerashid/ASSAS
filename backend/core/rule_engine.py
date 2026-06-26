from core.models import Subject, Enrolment, ExceptionLog, Student


class RuleEngine:
    """
    Executes academic rules in a fixed order for consistent, predictable
    subject assignment. Called by the Django backend when an admin triggers
    semester assignment for enrolled students.

    Rule order (from Chapter 3, Section 3.7.5):
      1. Already Passed Check
      2. Prerequisite Validation
      3. Credit Limit Check
      4. Repeat Subject Handling
      5. Probation Cap Enforcement
      6. Conflict Detection
    """

    def __init__(self, student: Student, semester: str):
        self.student = student
        self.semester = semester
        self.programme = student.programme
        self.assigned_subjects = []
        self.assigned_credits = 0
        self.exceptions = []
        self.credit_cap = student.effective_credit_cap

    def run(self):
        completed_codes = self._get_completed_subject_codes()
        failed_codes = self._get_failed_subject_codes()
        current_assigned_codes = self._get_current_semester_assigned_codes()

        semester_subjects = self._get_semester_subjects()

        failed_subjects = [s for s in Subject.objects.filter(
            subject_code__in=failed_codes,
            programme=self.programme
        )]
        regular_subjects = [s for s in semester_subjects if s.subject_code not in failed_codes]
        ordered_subjects = failed_subjects + regular_subjects

        for subject in ordered_subjects:
            result = self._evaluate_subject(
                subject, completed_codes, failed_codes, current_assigned_codes
            )

            if result['action'] == 'assign':
                self._assign_subject(subject, is_repeat=(subject.subject_code in failed_codes))
                completed_codes_set = set(completed_codes)
                current_assigned_codes.add(subject.subject_code)
            elif result['action'] == 'flag':
                self._flag_exception(subject, result['reason'], result.get('details', ''))

        return {
            'student_id': self.student.user.student_id,
            'semester': self.semester,
            'assigned': [s.subject_code for s in self.assigned_subjects],
            'assigned_credits': self.assigned_credits,
            'exceptions': self.exceptions,
        }

    def _evaluate_subject(self, subject, completed_codes, failed_codes, current_assigned_codes):
        # Rule 1: Already Passed Check
        if subject.subject_code in completed_codes:
            return {'action': 'skip', 'reason': 'already_passed'}

        # Rule 6: Conflict Detection (check before assigning)
        if subject.subject_code in current_assigned_codes:
            return {'action': 'skip', 'reason': 'already_assigned'}

        # Rule 2: Prerequisite Validation
        prerequisites = subject.prerequisites.all()
        for prereq in prerequisites:
            if prereq.prerequisite_subject.subject_code not in completed_codes:
                return {
                    'action': 'flag',
                    'reason': 'prerequisite_unmet',
                    'details': f'Missing prerequisite: {prereq.prerequisite_subject.subject_code} '
                               f'({prereq.prerequisite_subject.subject_name})',
                }

        # Rule 3 & 5: Credit Limit Check / Probation Cap
        if self.assigned_credits + subject.credit_hours > self.credit_cap:
            reason = 'probation_cap' if self.student.status == 'probation' else 'credit_limit_exceeded'
            return {
                'action': 'flag',
                'reason': reason,
                'details': f'Adding {subject.subject_code} ({subject.credit_hours} cr) would exceed '
                           f'limit of {self.credit_cap} credits. Currently assigned: {self.assigned_credits} cr.',
            }

        # Rule 4: Repeat Subject Handling (already prioritised in ordering)
        # If the subject is a failed subject, it's already been moved to the front.
        # We just note it as a repeat in the enrolment record.

        return {'action': 'assign'}

    def _assign_subject(self, subject, is_repeat=False):
        Enrolment.objects.create(
            student=self.student,
            subject=subject,
            semester=self.semester,
            status='assigned',
            is_repeat=is_repeat,
        )
        self.assigned_subjects.append(subject)
        self.assigned_credits += subject.credit_hours

    def _flag_exception(self, subject, reason, details=''):
        ExceptionLog.objects.create(
            student=self.student,
            subject=subject,
            reason=reason,
            details=details,
            status='pending',
        )
        self.exceptions.append({
            'subject_code': subject.subject_code,
            'subject_name': subject.subject_name,
            'reason': reason,
            'details': details,
        })

    def _get_completed_subject_codes(self):
        return set(
            Enrolment.objects.filter(
                student=self.student,
                status='passed',
            ).values_list('subject__subject_code', flat=True)
        )

    def _get_failed_subject_codes(self):
        passed = self._get_completed_subject_codes()
        failed = set(
            Enrolment.objects.filter(
                student=self.student,
                status='failed',
            ).values_list('subject__subject_code', flat=True)
        )
        return failed - passed

    def _get_current_semester_assigned_codes(self):
        return set(
            Enrolment.objects.filter(
                student=self.student,
                semester=self.semester,
                status__in=['assigned', 'in_progress'],
            ).values_list('subject__subject_code', flat=True)
        )

    def _get_semester_subjects(self):
        return Subject.objects.filter(
            programme=self.programme,
            year=self.student.current_year,
            semester=self.student.current_semester,
        )


def run_assignment_for_student(student: Student, semester: str):
    Enrolment.objects.filter(
        student=student,
        semester=semester,
        status='assigned',
    ).delete()
    ExceptionLog.objects.filter(
        student=student,
        subject__programme=student.programme,
        status='pending',
        created_at__isnull=False,
    ).filter(
        created_at__gte=student.user.date_joined,
    ).delete()

    engine = RuleEngine(student, semester)
    return engine.run()


def run_assignment_for_all(semester: str):
    students = Student.objects.filter(status__in=['active', 'probation'])
    results = []
    for student in students:
        result = run_assignment_for_student(student, semester)
        results.append(result)
    return results
