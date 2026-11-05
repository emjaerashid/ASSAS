from django.core.management.base import BaseCommand

from core.models import Enrolment, Faculty, Prerequisite, Programme, Rule, Student, Subject, User

# Curriculum is a flat sequence of semesters 1-9 (three a year). The final
# BCSSE subjects that used to sit in a fourth year are spread across 7-9,
# matching migration 0005_flatten_semesters.
SUBJECTS = [
    # code, name, credit hours, curriculum semester
    ('BCS1013', 'Introduction to Computer Science', 3, 1),
    ('BCS1023', 'Programming Fundamentals', 3, 1),
    ('BIT1013', 'Discrete Mathematics', 3, 1),
    ('BEN1013', 'English Communication I', 3, 1),

    ('BIT1023', 'Computer Organization & Architecture', 3, 2),
    ('MPU3113', 'Hubungan Etnik', 3, 2),
    ('MPU3123', 'Tamadun Islam dan Tamadun Asia', 3, 2),
    ('BIT1033', 'Mathematics for Computing', 3, 2),
    ('MPU3212', 'Community Service', 2, 2),

    ('BCS1033', 'Data Structures & Algorithms', 3, 3),
    ('BCS1043', 'Object-Oriented Programming', 3, 3),
    ('BIT1043', 'Database Systems', 3, 3),
    ('BEN1023', 'English Communication II', 3, 3),
    ('MPU3133', 'Bahasa Kebangsaan A', 3, 3),

    ('BCS2013', 'Software Engineering', 3, 4),
    ('BIT2013', 'Operating Systems', 3, 4),
    ('BIT2023', 'Computer Networks', 3, 4),
    ('MPU3143', 'Falsafah dan Isu Semasa', 3, 4),

    ('BCS2023', 'Web Programming', 3, 5),
    ('BIT2033', 'Statistics & Probability', 3, 5),
    ('BCS2033', 'Human-Computer Interaction', 3, 5),
    ('BIT2053', 'System Analysis & Design', 3, 5),

    ('BCS2043', 'Requirements Engineering', 3, 6),
    ('BCS2063', 'Software Design & Architecture', 3, 6),
    ('BIT2043', 'Information Security', 3, 6),
    ('BCS2053', 'Mobile Application Development', 3, 6),
    ('BEN2013', 'Technical Writing', 3, 6),
    ('BCS2072', 'Co-curriculum', 2, 6),

    ('BCS3033', 'Artificial Intelligence', 3, 7),
    ('BCS3043', 'Cloud Computing', 3, 7),
    ('BIT3013', 'Elective I', 3, 7),
    ('BIT3023', 'Professional Ethics in IT', 3, 7),
    ('BIT3033', 'Technopreneurship', 3, 7),
    ('BIT4016', 'Industrial Training', 6, 7),

    ('BCS3013', 'Software Testing & Quality Assurance', 3, 8),
    ('BCS3023', 'Software Project Management', 3, 8),
    ('BCS3063', 'Data Science Fundamentals', 3, 8),
    ('BCS3073', 'Advanced Database Systems', 3, 8),
    ('BIT4026', 'Project 2', 6, 8),

    ('BIT3043', 'Project 1', 3, 9),
    ('BCS3053', 'DevOps & Continuous Integration', 3, 9),
    ('BIT3053', 'Elective II', 3, 9),
    ('BIT3063', 'Elective III', 3, 9),
    ('BCS4013', 'Emerging Technologies', 3, 9),
    ('BIT4033', 'Elective IV', 3, 9),
]

# (subject, prerequisite)
PREREQUISITES = [
    ('BCS1033', 'BCS1023'), ('BCS1043', 'BCS1023'), ('BIT1043', 'BCS1013'), ('BEN1023', 'BEN1013'),
    ('BCS2013', 'BCS1043'), ('BCS2023', 'BCS1043'), ('BCS2023', 'BIT1043'), ('BIT2013', 'BIT1023'),
    ('BIT2023', 'BIT1023'), ('BCS2033', 'BCS1043'),
    ('BCS2043', 'BCS2013'), ('BCS2053', 'BCS2023'), ('BCS2063', 'BCS2013'), ('BIT2043', 'BIT2023'),
    ('BIT2053', 'BIT1043'),
    ('BCS3013', 'BCS2013'), ('BCS3013', 'BCS2063'), ('BCS3023', 'BCS2013'), ('BCS3033', 'BCS1033'),
    ('BCS3043', 'BIT2013'), ('BCS3043', 'BIT2023'),
    ('BIT3043', 'BCS3013'), ('BIT3043', 'BCS3023'), ('BCS3053', 'BCS3013'), ('BCS3063', 'BIT1043'),
    ('BCS3063', 'BIT2033'), ('BCS3073', 'BIT1043'),
    ('BIT4016', 'BIT3043'), ('BIT4026', 'BIT4016'),
]

OTHER_PROGRAMMES = [
    ('BCSAI', 'Bachelor of Computer Science (Artificial Intelligence) (Hons)', 133, 21, 12, 9),
    ('BCSCS', 'Bachelor of Computer Science (Cybersecurity) (Hons)', 133, 21, 12, 9),
    ('BIT', 'Bachelor of Information Technology (Hons)', 133, 21, 12, 9),
    ('DCS', 'Diploma of Computer Science', 90, 18, 10, 7),
]

# Sample students all joined the September 2022 intake (hence 202209... IDs).
# Each registration period is <year><01|05|09>, so their history runs
# 202209, 202301, 202305, ... one curriculum semester per period.
INTAKE_PERIODS = ['202209', '202301', '202305', '202309', '202401', '202405', '202409', '202501', '202505']

SAMPLE_STUDENTS = [
    # student_id, name, IC/passport, current curriculum semester, status
    ('202209020001', 'Ahmad Bin Hassan', '010515140001', 1, 'active'),
    ('202209020002', 'Nuru Rashid Matora', '020320140002', 8, 'active'),
    ('202209020003', 'Siti Aminah Binti Yusof', '030812140003', 4, 'active'),
    ('202209020004', 'David Tan Wei Ming', '040101140004', 5, 'probation'),
    ('202209020005', 'Priya Devi A/P Ramasamy', '050630140005', 2, 'active'),
]

# Grades per completed curriculum semester: a single grade for every subject
# that semester, or {subject: grade} overrides on top of a default, where a
# None grade means the subject wasn't taken. 'F' and 'D' mark a failed
# attempt; everything else is a pass.
SAMPLE_HISTORY = {
    # Industrial Training (semester 7) needs Project 1 (semester 9) first.
    '202209020002': {**{sem: 'B+' for sem in range(1, 7)}, 7: ('B+', {'BIT4016': None})},
    '202209020003': {1: 'A-', 2: 'B', 3: 'B'},
    '202209020004': {
        1: ('C', {'BCS1023': 'F'}),
        2: 'C+',
        3: ('C+', {'BCS1033': 'D', 'BCS1043': 'D'}),
        4: 'C',
    },
    '202209020005': {1: 'B'},
}
FAILING_GRADES = {'F', 'D'}


class Command(BaseCommand):
    help = 'Seed the database with the Faculty of IT programme structure and sample students'

    def handle(self, *args, **options):
        self.stdout.write('Seeding Faculty of Information Technology data...')

        faculty = self._create_faculty()
        programme = self._create_programme(faculty)
        self._create_other_programmes(faculty)
        subjects = self._create_subjects(programme)
        self._create_prerequisites(subjects)
        self._create_admin()
        self._create_sample_students(programme, subjects)

        self.stdout.write(self.style.SUCCESS('Seed data created successfully!'))

    def _create_faculty(self):
        faculty, _ = Faculty.objects.update_or_create(
            faculty_code='FIT',
            defaults={'faculty_name': 'Faculty of Information Technology'},
        )
        self.stdout.write(f'  Faculty: {faculty}')
        return faculty

    def _create_programme(self, faculty):
        programme, _ = Programme.objects.update_or_create(
            programme_code='BCSSE',
            defaults={
                'programme_name': 'Bachelor of Computer Science (Software Engineering) (Hons)',
                'faculty': faculty,
                'total_credits': 133,
                'max_credits_per_sem': 21,
                'probation_credit_cap': 12,
                'total_semesters': 9,
            },
        )
        self.stdout.write(f'  Programme: {programme}')
        self._create_rules(programme)
        return programme

    def _create_other_programmes(self, faculty):
        for code, name, total, max_credits, probation_cap, semesters in OTHER_PROGRAMMES:
            programme, _ = Programme.objects.update_or_create(
                programme_code=code,
                defaults={
                    'programme_name': name,
                    'faculty': faculty,
                    'total_credits': total,
                    'max_credits_per_sem': max_credits,
                    'probation_credit_cap': probation_cap,
                    'total_semesters': semesters,
                },
            )
            self.stdout.write(f'  Programme: {programme}')
            self._create_rules(programme)

    def _create_subjects(self, programme):
        subjects = {}
        for code, name, credits, semester in SUBJECTS:
            subject, _ = Subject.objects.update_or_create(
                subject_code=code,
                defaults={'subject_name': name, 'credit_hours': credits, 'semester': semester},
            )
            subject.programmes.add(programme)
            subjects[code] = subject
        self.stdout.write(f'  Subjects: {len(subjects)}')
        return subjects

    def _create_prerequisites(self, subjects):
        for subject_code, prereq_code in PREREQUISITES:
            Prerequisite.objects.get_or_create(
                subject=subjects[subject_code], prerequisite_subject=subjects[prereq_code],
            )
        self.stdout.write(f'  Prerequisites: {len(PREREQUISITES)}')

    def _create_rules(self, programme):
        rules = [
            ('max_credits', programme.max_credits_per_sem),
            ('probation_cap', programme.probation_credit_cap),
            ('min_credits', 3),
            ('max_repeat', 3),
        ]
        for rule_type, value in rules:
            Rule.objects.update_or_create(
                rule_type=rule_type,
                programme=programme,
                defaults={'rule_value': value, 'is_active': True},
            )

    def _create_admin(self):
        admin_user, created = User.objects.get_or_create(
            student_id='ADMIN001',
            defaults={
                'full_name': 'System Administrator',
                'ic_passport': 'ADMIN001',
                'role': 'admin',
                'is_staff': True,
                'is_superuser': True,
            },
        )
        if created:
            admin_user.set_password('ADMIN001')
            admin_user.save()
            self.stdout.write('  Admin user: ADMIN001 / ADMIN001')
        else:
            self.stdout.write('  Admin user already exists')

    def _create_sample_students(self, programme, subjects):
        codes_by_semester = {}
        for code, _, _, semester in SUBJECTS:
            codes_by_semester.setdefault(semester, []).append(code)

        for student_id, name, ic, current_semester, status in SAMPLE_STUDENTS:
            user, created = User.objects.get_or_create(
                student_id=student_id,
                defaults={'full_name': name, 'ic_passport': ic, 'role': 'student'},
            )
            if created:
                user.set_password(ic)
                user.save()

            student, _ = Student.objects.update_or_create(
                user=user,
                defaults={'programme': programme, 'current_semester': current_semester, 'status': status},
            )

            for curriculum_semester, grading in SAMPLE_HISTORY.get(student_id, {}).items():
                default_grade, overrides = grading if isinstance(grading, tuple) else (grading, {})
                for code in codes_by_semester[curriculum_semester]:
                    grade = overrides.get(code, default_grade)
                    if grade is None:
                        continue
                    Enrolment.objects.get_or_create(
                        student=student,
                        subject=subjects[code],
                        semester=INTAKE_PERIODS[curriculum_semester - 1],
                        defaults={
                            'status': 'failed' if grade in FAILING_GRADES else 'passed',
                            'grade': grade,
                        },
                    )

            # Credits and CGPA are derived from the enrolment history above.
            student.recompute_total_credits_earned()
            student.recompute_cgpa()

        self.stdout.write(f'  Sample students: {len(SAMPLE_STUDENTS)} (with enrolment history)')
