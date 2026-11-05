from django.db.models import Q
from django.utils import timezone

from core.models import Subject, Enrolment, ExceptionLog, Prerequisite, Student, TimeSlot, Venue

# Subjects in these final-year semesters (Industrial Training, Project 1/2,
# advanced electives) are never substituted in automatically - too
# consequential to swap without a human deliberately choosing.
AUTO_REPLACEMENT_EXCLUDED_SEMESTERS = {7, 8, 9}


def _venue_capacity(venue_name):
    """The seat capacity registered for this venue name, or None if it isn't
    a known capacity-limited venue (case/whitespace-insensitive, matching how
    TimeSlot.overlaps compares venues)."""
    if not venue_name:
        return None
    venue = Venue.objects.filter(name__iexact=venue_name.strip()).first()
    return venue.capacity if venue else None


def subject_seats_remaining(subject, programme, semester):
    """How many more students can be assigned into this subject's class for
    this programme+semester, or None if it isn't held in any capacity-limited
    venue. When a subject meets in more than one venue (e.g. lecture + lab),
    the most restrictive one caps it."""
    slots = TimeSlot.objects.filter(
        subject=subject, timetable__programmes=programme, timetable__semester=semester,
    )
    capacities = [c for c in (_venue_capacity(s.venue) for s in slots) if c is not None]
    if not capacities:
        return None
    occupied = Enrolment.objects.filter(
        subject=subject, semester=semester, status__in=['assigned', 'in_progress'],
    ).count()
    return min(capacities) - occupied


def is_subject_full(subject, programme, semester):
    remaining = subject_seats_remaining(subject, programme, semester)
    return remaining is not None and remaining <= 0


def is_dependent_subject(subject):
    """True if the subject has any prerequisite relationship at all - either
    it requires something, or something else requires it - making it unsafe
    to substitute automatically without a human reviewing the chronology
    impact."""
    return Prerequisite.objects.filter(
        Q(subject=subject) | Q(prerequisite_subject=subject)
    ).exists()


def is_safe_for_auto_replacement(subject):
    return subject.semester not in AUTO_REPLACEMENT_EXCLUDED_SEMESTERS and not is_dependent_subject(subject)


def find_clash_free_replacements(student, programme, semester, exclude_subject_code, safe_only=False):
    """Subjects (from any curriculum semester) that could stand in for a
    conflict-flagged subject: not already passed or assigned this semester,
    scheduled in this programme's timetable for this semester, and with no
    day/time overlap against the student's other subjects already assigned
    this semester (venue-double-booking within a timetable is already
    prevented when time slots are created, so day/time overlap is the
    relevant clash here regardless of venue), and not already at its own
    venue capacity. Semester 7-9 subjects are only ever offered to a student
    who is themselves in that matching semester - never as a cross-semester
    substitute. When safe_only=True, also excludes subjects with any
    prerequisite entanglement and semester 7-9 subjects entirely (even for a
    matching-semester student), for unattended automatic replacement rather
    than admin-reviewed manual replacement."""
    passed_codes = set(
        Enrolment.objects.filter(student=student, status='passed')
        .values_list('subject__subject_code', flat=True)
    )
    assigned_codes = set(
        Enrolment.objects.filter(
            student=student, semester=semester, status__in=['assigned', 'in_progress'],
        ).values_list('subject__subject_code', flat=True)
    )

    existing_slots = list(TimeSlot.objects.filter(
        subject__subject_code__in=assigned_codes,
        timetable__programmes=programme,
        timetable__semester=semester,
    ))

    candidates = Subject.objects.filter(
        programmes=programme,
        time_slots__timetable__programmes=programme,
        time_slots__timetable__semester=semester,
    ).exclude(
        subject_code=exclude_subject_code,
    ).exclude(
        subject_code__in=passed_codes | assigned_codes,
    ).distinct().order_by('semester', 'subject_code')

    # Semester 7-9 subjects (Industrial Training, Project 1/2, advanced
    # electives) are only ever valid for a student actually in that matching
    # semester - never offered as a substitute for a student elsewhere in
    # the programme, whether picked automatically or by an admin.
    candidates = candidates.exclude(
        Q(semester__in=AUTO_REPLACEMENT_EXCLUDED_SEMESTERS) & ~Q(semester=student.current_semester)
    )

    if safe_only:
        # Automatic replacement additionally never touches semester 7-9 at
        # all, even for a student who is themselves in one of those
        # semesters - too consequential to swap without a human choosing.
        candidates = candidates.exclude(semester__in=AUTO_REPLACEMENT_EXCLUDED_SEMESTERS)

    results = []
    for subject in candidates:
        if safe_only and is_dependent_subject(subject):
            continue
        if is_subject_full(subject, programme, semester):
            continue
        subject_slots = list(TimeSlot.objects.filter(
            subject=subject, timetable__programmes=programme, timetable__semester=semester,
        ))
        clashes = any(
            a.day_of_week == b.day_of_week and a.start_time < b.end_time and b.start_time < a.end_time
            for a in subject_slots for b in existing_slots
        )
        if not clashes:
            results.append((subject, subject_slots))
    return results


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
      7. Class Capacity Check
    """

    def __init__(self, student: Student, semester: str, max_subjects: int = None):
        self.student = student
        self.semester = semester
        self.programme = student.programme
        self.assigned_subjects = []
        self.assigned_credits = 0
        self.exceptions = []
        self.credit_cap = student.effective_credit_cap
        self.max_subjects = max_subjects

        # Subjects the student already holds this semester (e.g. from an
        # earlier run) count toward the credit cap and subject limit, so a
        # re-run only tops up to the limits instead of adding a full new load.
        existing = Enrolment.objects.filter(
            student=student, semester=semester, status__in=['assigned', 'in_progress'],
        ).select_related('subject')
        self.existing_subject_count = existing.count()
        self.existing_credits = sum(e.subject.credit_hours for e in existing)

    @property
    def total_credits(self):
        return self.existing_credits + self.assigned_credits

    @property
    def total_subjects(self):
        return self.existing_subject_count + len(self.assigned_subjects)

    def _has_room_for(self, subject):
        if self.total_credits + subject.credit_hours > self.credit_cap:
            return False
        return self.max_subjects is None or self.total_subjects < self.max_subjects

    def run(self):
        completed_codes = self._get_completed_subject_codes()
        failed_codes = self._get_failed_subject_codes()
        current_assigned_codes = self._get_current_semester_assigned_codes()

        semester_subjects = self._get_semester_subjects()

        failed_subjects = [s for s in self._with_scheduled_time_slot(Subject.objects.filter(
            subject_code__in=failed_codes,
            programmes=self.programme,
        ))]
        regular_subjects = [s for s in semester_subjects if s.subject_code not in failed_codes]
        ordered_subjects = failed_subjects + regular_subjects

        ordered_subjects, clash_losers = self._resolve_timeslot_clashes(ordered_subjects)

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
            elif result['action'] == 'full':
                self._handle_full_subject(subject)

        for loser, winner in clash_losers:
            self._handle_clash_loser(loser, winner)

        return {
            'student_id': self.student.user.student_id,
            'student_name': self.student.user.full_name,
            'current_semester': self.student.current_semester,
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
        if self.total_credits + subject.credit_hours > self.credit_cap:
            reason = 'probation_cap' if self.student.status == 'probation' else 'credit_limit_exceeded'
            return {
                'action': 'flag',
                'reason': reason,
                'details': f'Adding {subject.subject_code} ({subject.credit_hours} cr) would exceed '
                           f'limit of {self.credit_cap} credits. Currently assigned: {self.total_credits} cr.',
            }

        # Duration-based Subject Count Limit
        if self.max_subjects is not None and self.total_subjects >= self.max_subjects:
            return {
                'action': 'flag',
                'reason': 'subject_limit_exceeded',
                'details': f'Adding {subject.subject_code} would exceed the maximum of '
                           f'{self.max_subjects} subjects for this semester duration.',
            }

        # Rule 4: Repeat Subject Handling (already prioritised in ordering)
        # If the subject is a failed subject, it's already been moved to the front.
        # We just note it as a repeat in the enrolment record.

        # Rule 7: Class Capacity Check
        if is_subject_full(subject, self.programme, self.semester):
            return {'action': 'full'}

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

    def _handle_clash_loser(self, loser, winner):
        """A subject that lost a time-slot clash gets flagged as a conflict
        exception. If it's "safe" (not tangled up in prerequisites, and not
        a final-year semester 7-9 subject), try to auto-resolve it by
        substituting a clash-free replacement immediately, rather than
        leaving it for a coordinator to pick manually."""
        details = (
            f"Time clashes with {winner.subject_code} ({winner.subject_name}); {winner.subject_code} "
            f"was assigned instead as it carries more credit hours ({winner.credit_hours} vs {loser.credit_hours})."
        )
        exception = ExceptionLog.objects.create(
            student=self.student, subject=loser, reason='conflict', details=details, status='pending',
        )

        if is_safe_for_auto_replacement(loser):
            candidates = [
                c for c in find_clash_free_replacements(
                    self.student, self.programme, self.semester, loser.subject_code, safe_only=True,
                )
                if self._has_room_for(c[0])
            ]
            if candidates:
                replacement, _ = candidates[0]
                enrolment = Enrolment.objects.create(
                    student=self.student, subject=replacement, semester=self.semester, status='assigned',
                )
                note = (
                    f"Auto-resolved: substituted with {replacement.subject_code} ({replacement.subject_name}) "
                    f"- no prerequisite dependency and not a semester 7-9 subject."
                )
                exception.enrolment = enrolment
                exception.status = 'approved'
                exception.reviewed_at = timezone.now()
                exception.details = f"{details}\n{note}"
                exception.save()

                self.assigned_subjects.append(replacement)
                self.assigned_credits += replacement.credit_hours
                return

        self.exceptions.append({
            'subject_code': loser.subject_code,
            'subject_name': loser.subject_name,
            'reason': 'conflict',
            'details': details,
        })

    def _handle_full_subject(self, subject):
        """A subject whose venue has reached its student capacity gets
        flagged as a class-full exception. If it's "safe" (not tangled up in
        prerequisites, and not a final-year semester 7-9 subject), try to
        auto-resolve it by substituting a clash-free, non-full replacement
        immediately, same as a lost timetable clash."""
        details = f"{subject.subject_code} ({subject.subject_name}) has reached its class capacity."
        exception = ExceptionLog.objects.create(
            student=self.student, subject=subject, reason='class_full', details=details, status='pending',
        )

        if is_safe_for_auto_replacement(subject):
            candidates = [
                c for c in find_clash_free_replacements(
                    self.student, self.programme, self.semester, subject.subject_code, safe_only=True,
                )
                if self._has_room_for(c[0])
            ]
            if candidates:
                replacement, _ = candidates[0]
                enrolment = Enrolment.objects.create(
                    student=self.student, subject=replacement, semester=self.semester, status='assigned',
                )
                note = (
                    f"Auto-resolved: substituted with {replacement.subject_code} ({replacement.subject_name}) "
                    f"- no prerequisite dependency, not a semester 7-9 subject, and has capacity available."
                )
                exception.enrolment = enrolment
                exception.status = 'approved'
                exception.reviewed_at = timezone.now()
                exception.details = f"{details}\n{note}"
                exception.save()

                self.assigned_subjects.append(replacement)
                self.assigned_credits += replacement.credit_hours
                return

        self.exceptions.append({
            'subject_code': subject.subject_code,
            'subject_name': subject.subject_name,
            'reason': 'class_full',
            'details': details,
        })

    def required_subject_codes(self):
        """The set of subject codes this student should end up assigned for
        this semester: failed subjects due for a repeat, plus this curriculum
        semester's subjects that have a scheduled time slot, minus anything
        already passed. Used to decide whether re-running assignment for a
        student who already has some enrolments this semester would add
        anything new."""
        completed_codes = self._get_completed_subject_codes()
        failed_codes = self._get_failed_subject_codes()
        semester_codes = {s.subject_code for s in self._get_semester_subjects()}
        return (failed_codes | semester_codes) - completed_codes

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
        return self._with_scheduled_time_slot(Subject.objects.filter(
            programmes=self.programme,
            semester=self.student.current_semester,
        ))

    def _with_scheduled_time_slot(self, subjects_qs):
        """A subject can only be assigned once it has a class time slot
        registered in this programme's timetable for this semester."""
        return subjects_qs.filter(
            time_slots__timetable__programmes=self.programme,
            time_slots__timetable__semester=self.semester,
        ).distinct()

    def _resolve_timeslot_clashes(self, subjects):
        """A student can't attend two classes at the same day/time even if
        they're in different venues. When candidate subjects clash, keep only
        the one with the most credit hours; the rest are dropped from
        consideration (reported as scheduling-conflict exceptions)."""
        slots_by_code = {
            s.subject_code: list(TimeSlot.objects.filter(
                subject=s, timetable__programmes=self.programme, timetable__semester=self.semester,
            ))
            for s in subjects
        }
        excluded = {}  # subject_code -> winning Subject
        for i, subject_a in enumerate(subjects):
            if subject_a.subject_code in excluded:
                continue
            for subject_b in subjects[i + 1:]:
                if subject_b.subject_code in excluded:
                    continue
                if self._slots_clash(slots_by_code[subject_a.subject_code], slots_by_code[subject_b.subject_code]):
                    if subject_a.credit_hours >= subject_b.credit_hours:
                        excluded[subject_b.subject_code] = subject_a
                    else:
                        excluded[subject_a.subject_code] = subject_b
                        break

        winners = [s for s in subjects if s.subject_code not in excluded]
        losers = [(s, excluded[s.subject_code]) for s in subjects if s.subject_code in excluded]
        return winners, losers

    @staticmethod
    def _slots_clash(slots_a, slots_b):
        return any(
            a.day_of_week == b.day_of_week and a.start_time < b.end_time and b.start_time < a.end_time
            for a in slots_a for b in slots_b
        )


def run_assignment_for_student(student: Student, semester: str, max_subjects: int = None):
    existing = Enrolment.objects.filter(student=student, semester=semester)
    if existing.exists():
        required_codes = RuleEngine(student, semester, max_subjects=max_subjects).required_subject_codes()
        assigned_codes = set(
            existing.filter(status__in=['assigned', 'in_progress'])
            .values_list('subject__subject_code', flat=True)
        )
        if required_codes.issubset(assigned_codes):
            assigned = existing.filter(status='assigned').select_related('subject')
            return {
                'student_id': student.user.student_id,
                'student_name': student.user.full_name,
                'current_semester': student.current_semester,
                'semester': semester,
                'assigned': [e.subject.subject_code for e in assigned],
                'assigned_credits': sum(e.subject.credit_hours for e in assigned),
                'exceptions': [],
                'skipped': True,
            }
        # Student has some enrolments this semester but is still missing a
        # required subject (e.g. it lacked a time slot last run, or a
        # prerequisite/exception has since resolved) - fall through and
        # re-run so the engine can pick up what's still outstanding.

    ExceptionLog.objects.filter(
        student=student,
        subject__programmes=student.programme,
        status='pending',
        created_at__isnull=False,
    ).filter(
        created_at__gte=student.user.date_joined,
    ).delete()

    engine = RuleEngine(student, semester, max_subjects=max_subjects)
    return engine.run()


def run_assignment_for_all(semester: str, max_subjects: int = None, programme_code: str = None, faculty_code: str = None):
    students = Student.objects.filter(status__in=['active', 'probation'])
    if programme_code:
        students = students.filter(programme__programme_code=programme_code)
    if faculty_code:
        students = students.filter(programme__faculty__faculty_code=faculty_code)
    results = []
    for student in students:
        result = run_assignment_for_student(student, semester, max_subjects=max_subjects)
        results.append(result)
    return results
