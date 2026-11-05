from datetime import time
from decimal import Decimal

from django.test import TestCase

from core.models import (
    AddDropRequest, Enrolment, ExceptionLog, Faculty, Prerequisite, Programme,
    Student, Subject, TimeSlot, Timetable, User, Venue,
)
from core.rule_engine import (
    RuleEngine, find_clash_free_replacements, is_dependent_subject,
    is_safe_for_auto_replacement, is_subject_full, run_assignment_for_student,
    subject_seats_remaining,
)

CURRENT_SEM = '202401'


def make_user(student_id, role='student', **kwargs):
    return User.objects.create_user(
        student_id=student_id, password='pass1234',
        full_name=kwargs.pop('full_name', f'Student {student_id}'),
        ic_passport=kwargs.pop('ic_passport', '000000-00-0000'),
        role=role, **kwargs,
    )


def make_programme(code='BCS', **kwargs):
    return Programme.objects.create(
        programme_code=code, programme_name=f'{code} Programme', **kwargs,
    )


def make_subject(code, semester, credit_hours=3, programmes=None):
    subject = Subject.objects.create(
        subject_code=code, subject_name=f'Subject {code}',
        credit_hours=credit_hours, semester=semester,
    )
    for p in (programmes or []):
        subject.programmes.add(p)
    return subject


def make_student(student_id, programme, current_semester=1, status='active', **kwargs):
    user = make_user(student_id)
    return Student.objects.create(
        user=user, programme=programme, current_semester=current_semester,
        status=status, **kwargs,
    )


def make_venue(name, capacity):
    return Venue.objects.create(name=name, capacity=capacity)


def schedule(subject, programme, semester, day='mon', start=time(8, 0), end=time(10, 0), venue='A1'):
    timetable = Timetable.objects.create(title=f'TT-{subject.subject_code}', semester=semester)
    timetable.programmes.add(programme)
    return TimeSlot.objects.create(
        timetable=timetable, subject=subject, day_of_week=day,
        start_time=start, end_time=end, venue=venue,
    )


class StudentModelTests(TestCase):
    def setUp(self):
        self.programme = make_programme(max_credits_per_sem=21, probation_credit_cap=12)
        self.student = make_student('S001', self.programme)

    def test_effective_credit_cap_uses_probation_cap_when_on_probation(self):
        self.student.status = 'probation'
        self.assertEqual(self.student.effective_credit_cap, 12)

    def test_effective_credit_cap_uses_max_credits_when_active(self):
        self.assertEqual(self.student.effective_credit_cap, 21)

    def test_recompute_total_credits_earned_sums_only_passed(self):
        sub_a = make_subject('SUB1', 1, credit_hours=3, programmes=[self.programme])
        sub_b = make_subject('SUB2', 1, credit_hours=4, programmes=[self.programme])
        Enrolment.objects.create(student=self.student, subject=sub_a, semester=CURRENT_SEM, status='passed')
        Enrolment.objects.create(student=self.student, subject=sub_b, semester=CURRENT_SEM, status='failed')

        total = self.student.recompute_total_credits_earned()

        self.assertEqual(total, 3)
        self.student.refresh_from_db()
        self.assertEqual(self.student.total_credits_earned, 3)

    def test_recompute_total_credits_earned_skips_transfer_students(self):
        self.student.is_transfer = True
        self.student.total_credits_earned = 60
        self.student.save()
        sub_a = make_subject('SUB1', 1, credit_hours=3, programmes=[self.programme])
        Enrolment.objects.create(student=self.student, subject=sub_a, semester=CURRENT_SEM, status='passed')

        total = self.student.recompute_total_credits_earned()

        self.assertEqual(total, 60)

    def test_recompute_cgpa_weights_by_credit_hours(self):
        sub_a = make_subject('SUB1', 1, credit_hours=3, programmes=[self.programme])
        sub_b = make_subject('SUB2', 1, credit_hours=4, programmes=[self.programme])
        Enrolment.objects.create(student=self.student, subject=sub_a, semester=CURRENT_SEM, status='passed', grade='A')
        Enrolment.objects.create(student=self.student, subject=sub_b, semester=CURRENT_SEM, status='failed', grade='C')

        # (4.00*3 + 2.00*4) / 7 = 20/7 = 2.857... -> 2.86
        cgpa = self.student.recompute_cgpa()

        self.assertEqual(cgpa, Decimal('2.86'))

    def test_recompute_cgpa_ignores_ungraded_and_unrecognised_grades(self):
        sub_a = make_subject('SUB1', 1, credit_hours=3, programmes=[self.programme])
        sub_b = make_subject('SUB2', 1, credit_hours=4, programmes=[self.programme])
        Enrolment.objects.create(student=self.student, subject=sub_a, semester=CURRENT_SEM, status='assigned', grade='')
        Enrolment.objects.create(student=self.student, subject=sub_b, semester=CURRENT_SEM, status='passed', grade='A')

        cgpa = self.student.recompute_cgpa()

        self.assertEqual(cgpa, Decimal('4.00'))

    def test_recompute_cgpa_zero_when_no_graded_enrolments(self):
        self.assertEqual(self.student.recompute_cgpa(), Decimal('0.00'))

    def test_recompute_cgpa_skips_transfer_students(self):
        self.student.is_transfer = True
        self.student.cgpa = Decimal('3.50')
        self.student.save()
        sub_a = make_subject('SUB1', 1, credit_hours=3, programmes=[self.programme])
        Enrolment.objects.create(student=self.student, subject=sub_a, semester=CURRENT_SEM, status='passed', grade='C')

        cgpa = self.student.recompute_cgpa()

        self.assertEqual(cgpa, Decimal('3.50'))


class TimeSlotOverlapTests(TestCase):
    def setUp(self):
        self.programme = make_programme()
        self.subject = make_subject('SUB1', 1, programmes=[self.programme])
        self.timetable = Timetable.objects.create(title='TT', semester=CURRENT_SEM)
        self.timetable.programmes.add(self.programme)

    def _slot(self, day='mon', start=time(8, 0), end=time(10, 0), venue='A1'):
        return TimeSlot(
            timetable=self.timetable, subject=self.subject,
            day_of_week=day, start_time=start, end_time=end, venue=venue,
        )

    def test_overlaps_true_for_same_day_time_and_venue(self):
        a = self._slot(end=time(10, 0))
        b = self._slot(start=time(9, 0), end=time(11, 0))
        self.assertTrue(a.overlaps(b))
        self.assertTrue(b.overlaps(a))

    def test_overlaps_false_for_different_days(self):
        a = self._slot(day='mon')
        b = self._slot(day='tue')
        self.assertFalse(a.overlaps(b))

    def test_overlaps_false_for_non_overlapping_times(self):
        a = self._slot(start=time(8, 0), end=time(9, 0))
        b = self._slot(start=time(9, 0), end=time(10, 0))
        self.assertFalse(a.overlaps(b))

    def test_overlaps_false_for_different_venues(self):
        a = self._slot(venue='A1')
        b = self._slot(venue='B2')
        self.assertFalse(a.overlaps(b))

    def test_overlaps_ignores_venue_case_and_whitespace(self):
        a = self._slot(venue=' A1 ')
        b = self._slot(venue='a1')
        self.assertTrue(a.overlaps(b))


class RuleEngineBasicAssignmentTests(TestCase):
    def setUp(self):
        self.programme = make_programme(max_credits_per_sem=21, probation_credit_cap=12)
        self.student = make_student('S001', self.programme, current_semester=1)

    def test_assigns_subjects_with_scheduled_time_slots(self):
        sub = make_subject('SUB1', 1, credit_hours=3, programmes=[self.programme])
        schedule(sub, self.programme, CURRENT_SEM)

        result = RuleEngine(self.student, CURRENT_SEM).run()

        self.assertEqual(result['assigned'], ['SUB1'])
        self.assertEqual(result['assigned_credits'], 3)
        self.assertEqual(result['exceptions'], [])
        self.assertEqual(Enrolment.objects.filter(student=self.student, status='assigned').count(), 1)

    def test_skips_subjects_without_a_scheduled_time_slot(self):
        make_subject('SUB1', 1, credit_hours=3, programmes=[self.programme])

        result = RuleEngine(self.student, CURRENT_SEM).run()

        self.assertEqual(result['assigned'], [])
        self.assertEqual(Enrolment.objects.count(), 0)

    def test_already_passed_subject_is_not_reassigned(self):
        sub = make_subject('SUB1', 1, credit_hours=3, programmes=[self.programme])
        schedule(sub, self.programme, CURRENT_SEM)
        Enrolment.objects.create(student=self.student, subject=sub, semester='202309', status='passed')

        result = RuleEngine(self.student, CURRENT_SEM).run()

        self.assertEqual(result['assigned'], [])
        self.assertEqual(result['exceptions'], [])


class RuleEnginePrerequisiteTests(TestCase):
    def setUp(self):
        self.programme = make_programme()
        self.student = make_student('S001', self.programme, current_semester=2)

    def test_flags_exception_when_prerequisite_unmet(self):
        prereq = make_subject('SUB1', 1, programmes=[self.programme])
        sub = make_subject('SUB2', 2, programmes=[self.programme])
        Prerequisite.objects.create(subject=sub, prerequisite_subject=prereq)
        schedule(sub, self.programme, CURRENT_SEM)

        result = RuleEngine(self.student, CURRENT_SEM).run()

        self.assertEqual(result['assigned'], [])
        self.assertEqual(len(result['exceptions']), 1)
        self.assertEqual(result['exceptions'][0]['reason'], 'prerequisite_unmet')
        log = ExceptionLog.objects.get()
        self.assertEqual(log.reason, 'prerequisite_unmet')
        self.assertEqual(log.status, 'pending')

    def test_assigns_when_prerequisite_passed(self):
        prereq = make_subject('SUB1', 1, programmes=[self.programme])
        sub = make_subject('SUB2', 2, programmes=[self.programme])
        Prerequisite.objects.create(subject=sub, prerequisite_subject=prereq)
        schedule(sub, self.programme, CURRENT_SEM)
        Enrolment.objects.create(student=self.student, subject=prereq, semester='202309', status='passed')

        result = RuleEngine(self.student, CURRENT_SEM).run()

        self.assertEqual(result['assigned'], ['SUB2'])
        self.assertEqual(result['exceptions'], [])


class RuleEngineCreditLimitTests(TestCase):
    def setUp(self):
        self.programme = make_programme(max_credits_per_sem=6, probation_credit_cap=3)

    def test_flags_credit_limit_exceeded_for_active_student(self):
        student = make_student('S001', self.programme, current_semester=1, status='active')
        sub_a = make_subject('SUB1', 1, credit_hours=4, programmes=[self.programme])
        sub_b = make_subject('SUB2', 1, credit_hours=4, programmes=[self.programme])
        schedule(sub_a, self.programme, CURRENT_SEM, day='mon')
        schedule(sub_b, self.programme, CURRENT_SEM, day='tue')

        result = RuleEngine(student, CURRENT_SEM).run()

        self.assertEqual(result['assigned'], ['SUB1'])
        self.assertEqual(len(result['exceptions']), 1)
        self.assertEqual(result['exceptions'][0]['reason'], 'credit_limit_exceeded')

    def test_flags_probation_cap_for_probation_student(self):
        student = make_student('S001', self.programme, current_semester=1, status='probation')
        sub_a = make_subject('SUB1', 1, credit_hours=3, programmes=[self.programme])
        sub_b = make_subject('SUB2', 1, credit_hours=3, programmes=[self.programme])
        schedule(sub_a, self.programme, CURRENT_SEM, day='mon')
        schedule(sub_b, self.programme, CURRENT_SEM, day='tue')

        result = RuleEngine(student, CURRENT_SEM).run()

        self.assertEqual(result['assigned'], ['SUB1'])
        self.assertEqual(len(result['exceptions']), 1)
        self.assertEqual(result['exceptions'][0]['reason'], 'probation_cap')

    def test_max_subjects_flags_subject_limit_exceeded(self):
        student = make_student('S001', self.programme, current_semester=1, status='active')
        sub_a = make_subject('SUB1', 1, credit_hours=1, programmes=[self.programme])
        sub_b = make_subject('SUB2', 1, credit_hours=1, programmes=[self.programme])
        schedule(sub_a, self.programme, CURRENT_SEM, day='mon')
        schedule(sub_b, self.programme, CURRENT_SEM, day='tue')

        result = RuleEngine(student, CURRENT_SEM, max_subjects=1).run()

        self.assertEqual(result['assigned'], ['SUB1'])
        self.assertEqual(result['exceptions'][0]['reason'], 'subject_limit_exceeded')


class RuleEngineRepeatSubjectTests(TestCase):
    def setUp(self):
        self.programme = make_programme()
        self.student = make_student('S001', self.programme, current_semester=2)

    def test_failed_subject_is_reassigned_and_marked_repeat(self):
        failed_sub = make_subject('SUB1', 1, programmes=[self.programme])
        schedule(failed_sub, self.programme, CURRENT_SEM)
        Enrolment.objects.create(student=self.student, subject=failed_sub, semester='202309', status='failed')

        result = RuleEngine(self.student, CURRENT_SEM).run()

        self.assertIn('SUB1', result['assigned'])
        enrolment = Enrolment.objects.get(student=self.student, subject=failed_sub, semester=CURRENT_SEM)
        self.assertTrue(enrolment.is_repeat)

    def test_failed_then_passed_is_not_treated_as_failed(self):
        sub = make_subject('SUB1', 1, programmes=[self.programme])
        schedule(sub, self.programme, CURRENT_SEM)
        Enrolment.objects.create(student=self.student, subject=sub, semester='202309', status='failed')
        Enrolment.objects.create(student=self.student, subject=sub, semester='202401', status='passed')

        result = RuleEngine(self.student, '202405').run()

        self.assertEqual(result['assigned'], [])


class RuleEngineConflictDetectionTests(TestCase):
    def setUp(self):
        self.programme = make_programme(max_credits_per_sem=21)
        self.student = make_student('S001', self.programme, current_semester=1)

    def test_clashing_subjects_keep_higher_credit_winner(self):
        low = make_subject('LOW', 1, credit_hours=2, programmes=[self.programme])
        high = make_subject('HIGH', 1, credit_hours=4, programmes=[self.programme])
        schedule(low, self.programme, CURRENT_SEM, day='mon', start=time(8, 0), end=time(10, 0))
        schedule(high, self.programme, CURRENT_SEM, day='mon', start=time(9, 0), end=time(11, 0))

        result = RuleEngine(self.student, CURRENT_SEM).run()

        self.assertEqual(result['assigned'], ['HIGH'])
        exception = ExceptionLog.objects.get(subject=low)
        self.assertEqual(exception.reason, 'conflict')

    def test_non_clashing_subjects_are_both_assigned(self):
        sub_a = make_subject('SUB1', 1, credit_hours=3, programmes=[self.programme])
        sub_b = make_subject('SUB2', 1, credit_hours=3, programmes=[self.programme])
        schedule(sub_a, self.programme, CURRENT_SEM, day='mon', start=time(8, 0), end=time(10, 0))
        schedule(sub_b, self.programme, CURRENT_SEM, day='mon', start=time(10, 0), end=time(12, 0))

        result = RuleEngine(self.student, CURRENT_SEM).run()

        self.assertEqual(set(result['assigned']), {'SUB1', 'SUB2'})

    def test_clash_loser_auto_replaced_when_safe(self):
        # REPL is a different curriculum semester so it's not swept into the
        # student's regular semester-1 assignment loop; it's only reachable
        # here via the clash-loser auto-replacement search.
        low = make_subject('LOW', 1, credit_hours=2, programmes=[self.programme])
        high = make_subject('HIGH', 1, credit_hours=4, programmes=[self.programme])
        replacement = make_subject('REPL', 2, credit_hours=2, programmes=[self.programme])
        schedule(low, self.programme, CURRENT_SEM, day='mon', start=time(8, 0), end=time(10, 0))
        schedule(high, self.programme, CURRENT_SEM, day='mon', start=time(9, 0), end=time(11, 0))
        schedule(replacement, self.programme, CURRENT_SEM, day='tue', start=time(8, 0), end=time(10, 0))

        result = RuleEngine(self.student, CURRENT_SEM).run()

        self.assertEqual(set(result['assigned']), {'HIGH', 'REPL'})
        exception = ExceptionLog.objects.get(subject=low)
        self.assertEqual(exception.status, 'approved')
        self.assertIsNotNone(exception.enrolment)
        self.assertEqual(exception.enrolment.subject, replacement)

    def test_clash_loser_not_auto_replaced_when_final_year_semester(self):
        self.student.current_semester = 7
        self.student.save()
        low = make_subject('LOW', 7, credit_hours=2, programmes=[self.programme])
        high = make_subject('HIGH', 7, credit_hours=4, programmes=[self.programme])
        replacement = make_subject('REPL', 6, credit_hours=2, programmes=[self.programme])
        schedule(low, self.programme, CURRENT_SEM, day='mon', start=time(8, 0), end=time(10, 0))
        schedule(high, self.programme, CURRENT_SEM, day='mon', start=time(9, 0), end=time(11, 0))
        schedule(replacement, self.programme, CURRENT_SEM, day='tue', start=time(8, 0), end=time(10, 0))

        result = RuleEngine(self.student, CURRENT_SEM).run()

        self.assertEqual(result['assigned'], ['HIGH'])
        exception = ExceptionLog.objects.get(subject=low)
        self.assertEqual(exception.status, 'pending')
        self.assertIsNone(exception.enrolment)

    def test_clash_loser_not_auto_replaced_when_dependent_subject(self):
        low = make_subject('LOW', 1, credit_hours=2, programmes=[self.programme])
        high = make_subject('HIGH', 1, credit_hours=4, programmes=[self.programme])
        other = make_subject('OTHER', 2, credit_hours=3, programmes=[self.programme])
        Prerequisite.objects.create(subject=other, prerequisite_subject=low)
        replacement = make_subject('REPL', 3, credit_hours=2, programmes=[self.programme])
        schedule(low, self.programme, CURRENT_SEM, day='mon', start=time(8, 0), end=time(10, 0))
        schedule(high, self.programme, CURRENT_SEM, day='mon', start=time(9, 0), end=time(11, 0))
        schedule(replacement, self.programme, CURRENT_SEM, day='tue', start=time(8, 0), end=time(10, 0))

        result = RuleEngine(self.student, CURRENT_SEM).run()

        self.assertEqual(result['assigned'], ['HIGH'])
        exception = ExceptionLog.objects.get(subject=low)
        self.assertEqual(exception.status, 'pending')


class HelperFunctionTests(TestCase):
    def setUp(self):
        self.programme = make_programme()

    def test_is_dependent_subject_true_when_has_prerequisite(self):
        prereq = make_subject('SUB1', 1, programmes=[self.programme])
        sub = make_subject('SUB2', 2, programmes=[self.programme])
        Prerequisite.objects.create(subject=sub, prerequisite_subject=prereq)

        self.assertTrue(is_dependent_subject(sub))
        self.assertTrue(is_dependent_subject(prereq))

    def test_is_dependent_subject_false_when_no_relationship(self):
        sub = make_subject('SUB1', 1, programmes=[self.programme])
        self.assertFalse(is_dependent_subject(sub))

    def test_is_safe_for_auto_replacement_false_for_final_year_semester(self):
        sub = make_subject('SUB1', 7, programmes=[self.programme])
        self.assertFalse(is_safe_for_auto_replacement(sub))

    def test_is_safe_for_auto_replacement_true_for_independent_regular_subject(self):
        sub = make_subject('SUB1', 3, programmes=[self.programme])
        self.assertTrue(is_safe_for_auto_replacement(sub))

    def test_find_clash_free_replacements_excludes_passed_and_assigned(self):
        student = make_student('S001', self.programme, current_semester=1)
        passed = make_subject('PASSED', 1, programmes=[self.programme])
        assigned = make_subject('ASSIGNED', 1, programmes=[self.programme])
        candidate = make_subject('CAND', 1, programmes=[self.programme])
        schedule(passed, self.programme, CURRENT_SEM, day='mon')
        schedule(assigned, self.programme, CURRENT_SEM, day='tue')
        schedule(candidate, self.programme, CURRENT_SEM, day='wed')
        Enrolment.objects.create(student=student, subject=passed, semester='202309', status='passed')
        Enrolment.objects.create(student=student, subject=assigned, semester=CURRENT_SEM, status='assigned')

        results = find_clash_free_replacements(student, self.programme, CURRENT_SEM, exclude_subject_code='NONE')

        codes = [s.subject_code for s, _ in results]
        self.assertEqual(codes, ['CAND'])

    def test_find_clash_free_replacements_excludes_clashing_subjects(self):
        student = make_student('S001', self.programme, current_semester=1)
        assigned = make_subject('ASSIGNED', 1, programmes=[self.programme])
        clashing = make_subject('CLASH', 1, programmes=[self.programme])
        free = make_subject('FREE', 1, programmes=[self.programme])
        schedule(assigned, self.programme, CURRENT_SEM, day='mon', start=time(8, 0), end=time(10, 0))
        schedule(clashing, self.programme, CURRENT_SEM, day='mon', start=time(9, 0), end=time(11, 0))
        schedule(free, self.programme, CURRENT_SEM, day='tue', start=time(8, 0), end=time(10, 0))
        Enrolment.objects.create(student=student, subject=assigned, semester=CURRENT_SEM, status='assigned')

        results = find_clash_free_replacements(student, self.programme, CURRENT_SEM, exclude_subject_code='NONE')

        codes = [s.subject_code for s, _ in results]
        self.assertEqual(codes, ['FREE'])


class RunAssignmentForStudentTests(TestCase):
    def setUp(self):
        self.programme = make_programme()
        self.student = make_student('S001', self.programme, current_semester=1)

    def test_returns_existing_assignment_without_rerunning_when_already_satisfied(self):
        sub = make_subject('SUB1', 1, credit_hours=3, programmes=[self.programme])
        schedule(sub, self.programme, CURRENT_SEM)
        Enrolment.objects.create(student=self.student, subject=sub, semester=CURRENT_SEM, status='assigned')

        result = run_assignment_for_student(self.student, CURRENT_SEM)

        self.assertTrue(result['skipped'])
        self.assertEqual(result['assigned'], ['SUB1'])
        self.assertEqual(Enrolment.objects.filter(student=self.student).count(), 1)

    def test_reruns_when_existing_enrolments_miss_a_required_subject(self):
        sub_a = make_subject('SUB1', 1, credit_hours=3, programmes=[self.programme])
        sub_b = make_subject('SUB2', 1, credit_hours=3, programmes=[self.programme])
        schedule(sub_a, self.programme, CURRENT_SEM, day='mon')
        Enrolment.objects.create(student=self.student, subject=sub_a, semester=CURRENT_SEM, status='assigned')
        # SUB2 gets its time slot only now, so a rerun should pick it up.
        schedule(sub_b, self.programme, CURRENT_SEM, day='tue')

        result = run_assignment_for_student(self.student, CURRENT_SEM)

        # A rerun's `assigned` list is only what it newly assigned this pass;
        # SUB1 was already enrolled beforehand and is skipped as a duplicate.
        self.assertNotIn('skipped', result)
        self.assertEqual(result['assigned'], ['SUB2'])
        assigned_codes = set(
            Enrolment.objects.filter(student=self.student, semester=CURRENT_SEM, status='assigned')
            .values_list('subject__subject_code', flat=True)
        )
        self.assertEqual(assigned_codes, {'SUB1', 'SUB2'})

    def test_fresh_run_creates_enrolments(self):
        sub = make_subject('SUB1', 1, credit_hours=3, programmes=[self.programme])
        schedule(sub, self.programme, CURRENT_SEM)

        result = run_assignment_for_student(self.student, CURRENT_SEM)

        self.assertNotIn('skipped', result)
        self.assertEqual(result['assigned'], ['SUB1'])

    def test_rerun_counts_existing_enrolments_toward_subject_limit(self):
        existing = [make_subject(f'OLD{i}', 2, programmes=[self.programme]) for i in range(2)]
        for sub in existing:
            Enrolment.objects.create(student=self.student, subject=sub, semester=CURRENT_SEM, status='assigned')
        for i, day in enumerate(['mon', 'tue', 'wed']):
            schedule(make_subject(f'NEW{i}', 1, programmes=[self.programme]), self.programme, CURRENT_SEM, day=day)

        result = run_assignment_for_student(self.student, CURRENT_SEM, max_subjects=3)

        # Two already held + one top-up reaches the limit of 3; the rest are flagged.
        self.assertEqual(len(result['assigned']), 1)
        self.assertEqual([e['reason'] for e in result['exceptions']], ['subject_limit_exceeded'] * 2)
        self.assertEqual(
            Enrolment.objects.filter(student=self.student, semester=CURRENT_SEM, status='assigned').count(), 3,
        )

    def test_rerun_counts_existing_credits_toward_credit_cap(self):
        programme = make_programme('CAP', max_credits_per_sem=6)
        student = make_student('S002', programme, current_semester=1)
        held = make_subject('HELD', 2, credit_hours=3, programmes=[programme])
        Enrolment.objects.create(student=student, subject=held, semester=CURRENT_SEM, status='assigned')
        schedule(make_subject('NEW1', 1, credit_hours=3, programmes=[programme]), programme, CURRENT_SEM, day='mon')
        schedule(make_subject('NEW2', 1, credit_hours=3, programmes=[programme]), programme, CURRENT_SEM, day='tue')

        result = run_assignment_for_student(student, CURRENT_SEM)

        self.assertEqual(result['assigned'], ['NEW1'])
        self.assertEqual(result['exceptions'][0]['reason'], 'credit_limit_exceeded')
        self.assertIn('Currently assigned: 6 cr', result['exceptions'][0]['details'])

    def test_clash_auto_replacement_respects_subject_limit(self):
        winner = make_subject('WIN', 1, credit_hours=4, programmes=[self.programme])
        loser = make_subject('LOSE', 1, credit_hours=3, programmes=[self.programme])
        spare = make_subject('SPARE', 2, credit_hours=3, programmes=[self.programme])
        schedule(winner, self.programme, CURRENT_SEM, day='mon')
        schedule(loser, self.programme, CURRENT_SEM, day='mon')
        schedule(spare, self.programme, CURRENT_SEM, day='fri')

        result = RuleEngine(self.student, CURRENT_SEM, max_subjects=1).run()

        # WIN fills the only slot, so LOSE's conflict stays pending for a
        # coordinator instead of being auto-substituted with SPARE.
        self.assertEqual(result['assigned'], ['WIN'])
        self.assertFalse(Enrolment.objects.filter(student=self.student, subject=spare).exists())
        exception = ExceptionLog.objects.get(student=self.student, subject=loser)
        self.assertEqual((exception.reason, exception.status), ('conflict', 'pending'))


class SubjectSeatsRemainingTests(TestCase):
    def setUp(self):
        self.programme = make_programme()

    def test_uncapped_venue_returns_none_and_never_full(self):
        sub = make_subject('SUB1', 1, programmes=[self.programme])
        schedule(sub, self.programme, CURRENT_SEM, venue='Unlisted Room')

        self.assertIsNone(subject_seats_remaining(sub, self.programme, CURRENT_SEM))
        self.assertFalse(is_subject_full(sub, self.programme, CURRENT_SEM))

    def test_capped_venue_computes_remaining_seats(self):
        make_venue('Test Lab A', 2)
        sub = make_subject('SUB1', 1, programmes=[self.programme])
        schedule(sub, self.programme, CURRENT_SEM, venue='Test Lab A')
        student = make_student('S001', self.programme)
        Enrolment.objects.create(student=student, subject=sub, semester=CURRENT_SEM, status='assigned')

        self.assertEqual(subject_seats_remaining(sub, self.programme, CURRENT_SEM), 1)
        self.assertFalse(is_subject_full(sub, self.programme, CURRENT_SEM))

    def test_subject_full_when_occupied_reaches_capacity(self):
        make_venue('Test Lab A', 1)
        sub = make_subject('SUB1', 1, programmes=[self.programme])
        schedule(sub, self.programme, CURRENT_SEM, venue='Test Lab A')
        student = make_student('S001', self.programme)
        Enrolment.objects.create(student=student, subject=sub, semester=CURRENT_SEM, status='assigned')

        self.assertEqual(subject_seats_remaining(sub, self.programme, CURRENT_SEM), 0)
        self.assertTrue(is_subject_full(sub, self.programme, CURRENT_SEM))

    def test_venue_lookup_is_case_and_whitespace_insensitive(self):
        make_venue('Test Lab A', 1)
        sub = make_subject('SUB1', 1, programmes=[self.programme])
        schedule(sub, self.programme, CURRENT_SEM, venue=' test lab a ')

        self.assertEqual(subject_seats_remaining(sub, self.programme, CURRENT_SEM), 1)

    def test_multiple_venues_use_the_most_restrictive_capacity(self):
        make_venue('Test Lab A', 30)
        make_venue('Test Room A', 50)
        sub = make_subject('SUB1', 1, programmes=[self.programme])
        schedule(sub, self.programme, CURRENT_SEM, day='mon', venue='Test Room A')
        schedule(sub, self.programme, CURRENT_SEM, day='tue', venue='Test Lab A')

        self.assertEqual(subject_seats_remaining(sub, self.programme, CURRENT_SEM), 30)


class FindClashFreeReplacementsCapacityTests(TestCase):
    def setUp(self):
        self.programme = make_programme()
        self.student = make_student('S001', self.programme, current_semester=1)

    def test_excludes_full_candidates(self):
        make_venue('Test Lab A', 1)
        full_sub = make_subject('FULL', 1, programmes=[self.programme])
        free_sub = make_subject('FREE', 1, programmes=[self.programme])
        schedule(full_sub, self.programme, CURRENT_SEM, day='mon', venue='Test Lab A')
        schedule(free_sub, self.programme, CURRENT_SEM, day='tue', venue='Test Lab A')
        other_student = make_student('S002', self.programme)
        Enrolment.objects.create(student=other_student, subject=full_sub, semester=CURRENT_SEM, status='assigned')

        results = find_clash_free_replacements(self.student, self.programme, CURRENT_SEM, exclude_subject_code='NONE')

        codes = [s.subject_code for s, _ in results]
        self.assertEqual(codes, ['FREE'])


class RuleEngineCapacityTests(TestCase):
    def setUp(self):
        self.programme = make_programme(max_credits_per_sem=21)
        self.student = make_student('S001', self.programme, current_semester=1)

    def test_full_subject_without_replacement_is_flagged_pending(self):
        make_venue('Test Lab A', 1)
        sub = make_subject('SUB1', 1, credit_hours=3, programmes=[self.programme])
        schedule(sub, self.programme, CURRENT_SEM, venue='Test Lab A')
        other_student = make_student('S002', self.programme)
        Enrolment.objects.create(student=other_student, subject=sub, semester=CURRENT_SEM, status='assigned')

        result = RuleEngine(self.student, CURRENT_SEM).run()

        self.assertEqual(result['assigned'], [])
        self.assertEqual(len(result['exceptions']), 1)
        self.assertEqual(result['exceptions'][0]['reason'], 'class_full')
        exception = ExceptionLog.objects.get(student=self.student, subject=sub)
        self.assertEqual(exception.status, 'pending')
        self.assertIsNone(exception.enrolment)

    def test_full_subject_auto_replaced_with_available_class(self):
        # REPL is a different curriculum semester so it's not swept into the
        # student's regular semester-1 assignment loop; it's only reachable
        # here via the class-full auto-replacement search.
        make_venue('Test Lab A', 1)
        sub = make_subject('SUB1', 1, credit_hours=3, programmes=[self.programme])
        schedule(sub, self.programme, CURRENT_SEM, day='mon', venue='Test Lab A')
        other_student = make_student('S002', self.programme)
        Enrolment.objects.create(student=other_student, subject=sub, semester=CURRENT_SEM, status='assigned')

        replacement = make_subject('REPL', 2, credit_hours=3, programmes=[self.programme])
        schedule(replacement, self.programme, CURRENT_SEM, day='tue', venue='C999')

        result = RuleEngine(self.student, CURRENT_SEM).run()

        self.assertEqual(result['assigned'], ['REPL'])
        exception = ExceptionLog.objects.get(student=self.student, subject=sub)
        self.assertEqual(exception.status, 'approved')
        self.assertIsNotNone(exception.enrolment)
        self.assertEqual(exception.enrolment.subject, replacement)

    def test_full_replacement_candidate_is_skipped_for_the_next_option(self):
        make_venue('Test Lab A', 1)
        make_venue('Test Lab B', 1)
        sub = make_subject('SUB1', 1, credit_hours=3, programmes=[self.programme])
        schedule(sub, self.programme, CURRENT_SEM, day='mon', venue='Test Lab A')
        other_student = make_student('S002', self.programme)
        Enrolment.objects.create(student=other_student, subject=sub, semester=CURRENT_SEM, status='assigned')

        # Sorts before BOPEN, so the engine must try it first, find it full,
        # and move on to the next candidate rather than stopping there.
        full_candidate = make_subject('AFULL', 2, credit_hours=3, programmes=[self.programme])
        schedule(full_candidate, self.programme, CURRENT_SEM, day='tue', venue='Test Lab B')
        another_student = make_student('S003', self.programme)
        Enrolment.objects.create(student=another_student, subject=full_candidate, semester=CURRENT_SEM, status='assigned')

        open_candidate = make_subject('BOPEN', 2, credit_hours=3, programmes=[self.programme])
        schedule(open_candidate, self.programme, CURRENT_SEM, day='wed', venue='Test Lab B')

        result = RuleEngine(self.student, CURRENT_SEM).run()

        self.assertEqual(result['assigned'], ['BOPEN'])
        exception = ExceptionLog.objects.get(student=self.student, subject=sub)
        self.assertEqual(exception.enrolment.subject, open_candidate)

    def test_full_subject_not_auto_replaced_when_final_year_semester(self):
        self.student.current_semester = 7
        self.student.save()
        make_venue('Test Lab A', 1)
        sub = make_subject('SUB1', 7, credit_hours=3, programmes=[self.programme])
        schedule(sub, self.programme, CURRENT_SEM, day='mon', venue='Test Lab A')
        other_student = make_student('S002', self.programme, current_semester=7)
        Enrolment.objects.create(student=other_student, subject=sub, semester=CURRENT_SEM, status='assigned')

        replacement = make_subject('REPL', 6, credit_hours=3, programmes=[self.programme])
        schedule(replacement, self.programme, CURRENT_SEM, day='tue', venue='C999')

        result = RuleEngine(self.student, CURRENT_SEM).run()

        self.assertEqual(result['assigned'], [])
        exception = ExceptionLog.objects.get(student=self.student, subject=sub)
        self.assertEqual(exception.status, 'pending')
        self.assertIsNone(exception.enrolment)

    def test_full_subject_not_auto_replaced_when_dependent_subject(self):
        make_venue('Test Lab A', 1)
        sub = make_subject('SUB1', 1, credit_hours=3, programmes=[self.programme])
        other = make_subject('OTHER', 2, credit_hours=3, programmes=[self.programme])
        Prerequisite.objects.create(subject=other, prerequisite_subject=sub)
        schedule(sub, self.programme, CURRENT_SEM, day='mon', venue='Test Lab A')
        other_student = make_student('S002', self.programme)
        Enrolment.objects.create(student=other_student, subject=sub, semester=CURRENT_SEM, status='assigned')

        replacement = make_subject('REPL', 3, credit_hours=3, programmes=[self.programme])
        schedule(replacement, self.programme, CURRENT_SEM, day='tue', venue='C999')

        result = RuleEngine(self.student, CURRENT_SEM).run()

        self.assertEqual(result['assigned'], [])
        exception = ExceptionLog.objects.get(student=self.student, subject=sub)
        self.assertEqual(exception.status, 'pending')



class AdminStudentEditPasswordTests(TestCase):
    def setUp(self):
        from rest_framework.test import APIClient
        self.client = APIClient()
        self.student = make_student('S900', make_programme())
        self.user = self.student.user
        self.user.ic_passport = 'IC900'
        self.user.set_password('custom-secret')
        self.user.save()
        self.client.force_login(make_user('ADM1', role='admin', is_staff=True))
        self.url = '/api/admin/students/S900/'

    def test_edit_that_resends_same_ic_keeps_password(self):
        self.client.put(self.url, {'full_name': 'Renamed', 'ic_passport': 'IC900'}, format='multipart')
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('custom-secret'))

    def test_changing_ic_resets_password_to_new_ic(self):
        self.client.put(self.url, {'ic_passport': 'IC901'}, format='multipart')
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('IC901'))
