from django.core.management.base import BaseCommand
from core.models import User, Programme, Student, Subject, Prerequisite, Rule


class Command(BaseCommand):
    help = 'Seed the database with BCSSE programme structure and sample students'

    def handle(self, *args, **options):
        self.stdout.write('Seeding BCSSE programme data...')

        programme = self._create_programme()
        subjects = self._create_subjects(programme)
        self._create_prerequisites(subjects)
        self._create_rules(programme)
        self._create_admin()
        self._create_sample_students(programme)

        self.stdout.write(self.style.SUCCESS('Seed data created successfully!'))

    def _create_programme(self):
        programme, _ = Programme.objects.update_or_create(
            programme_code='BCSSE',
            defaults={
                'programme_name': 'Bachelor of Computer Science (Software Engineering)',
                'total_credits': 133,
                'max_credits_per_sem': 21,
                'probation_credit_cap': 12,
                'total_semesters': 8,
            },
        )
        self.stdout.write(f'  Programme: {programme}')
        return programme

    def _create_subjects(self, programme):
        subject_data = [
            # Year 1, Semester 1
            ('BCS1013', 'Introduction to Computer Science', 3, 1, 1),
            ('BCS1023', 'Programming Fundamentals', 3, 1, 1),
            ('BIT1013', 'Discrete Mathematics', 3, 1, 1),
            ('BIT1023', 'Computer Organization & Architecture', 3, 1, 1),
            ('MPU3113', 'Hubungan Etnik', 3, 1, 1),
            ('MPU3123', 'Tamadun Islam dan Tamadun Asia', 3, 1, 1),
            ('BEN1013', 'English Communication I', 3, 1, 1),

            # Year 1, Semester 2
            ('BCS1033', 'Data Structures & Algorithms', 3, 1, 2),
            ('BCS1043', 'Object-Oriented Programming', 3, 1, 2),
            ('BIT1033', 'Mathematics for Computing', 3, 1, 2),
            ('BIT1043', 'Database Systems', 3, 1, 2),
            ('BEN1023', 'English Communication II', 3, 1, 2),
            ('MPU3133', 'Bahasa Kebangsaan A', 3, 1, 2),
            ('MPU3212', 'Community Service', 2, 1, 2),

            # Year 2, Semester 1
            ('BCS2013', 'Software Engineering', 3, 2, 1),
            ('BCS2023', 'Web Programming', 3, 2, 1),
            ('BIT2013', 'Operating Systems', 3, 2, 1),
            ('BIT2023', 'Computer Networks', 3, 2, 1),
            ('BIT2033', 'Statistics & Probability', 3, 2, 1),
            ('BCS2033', 'Human-Computer Interaction', 3, 2, 1),
            ('MPU3143', 'Falsafah dan Isu Semasa', 3, 2, 1),

            # Year 2, Semester 2
            ('BCS2043', 'Requirements Engineering', 3, 2, 2),
            ('BCS2053', 'Mobile Application Development', 3, 2, 2),
            ('BCS2063', 'Software Design & Architecture', 3, 2, 2),
            ('BIT2043', 'Information Security', 3, 2, 2),
            ('BIT2053', 'System Analysis & Design', 3, 2, 2),
            ('BEN2013', 'Technical Writing', 3, 2, 2),
            ('BCS2072', 'Co-curriculum', 2, 2, 2),

            # Year 3, Semester 1
            ('BCS3013', 'Software Testing & Quality Assurance', 3, 3, 1),
            ('BCS3023', 'Software Project Management', 3, 3, 1),
            ('BCS3033', 'Artificial Intelligence', 3, 3, 1),
            ('BCS3043', 'Cloud Computing', 3, 3, 1),
            ('BIT3013', 'Elective I', 3, 3, 1),
            ('BIT3023', 'Professional Ethics in IT', 3, 3, 1),
            ('BIT3033', 'Technopreneurship', 3, 3, 1),

            # Year 3, Semester 2
            ('BIT3043', 'Project 1', 3, 3, 2),
            ('BCS3053', 'DevOps & Continuous Integration', 3, 3, 2),
            ('BCS3063', 'Data Science Fundamentals', 3, 3, 2),
            ('BIT3053', 'Elective II', 3, 3, 2),
            ('BIT3063', 'Elective III', 3, 3, 2),
            ('BCS3073', 'Advanced Database Systems', 3, 3, 2),

            # Year 4, Semester 1
            ('BIT4016', 'Industrial Training', 6, 4, 1),

            # Year 4, Semester 2
            ('BIT4026', 'Project 2', 6, 4, 2),
            ('BCS4013', 'Emerging Technologies', 3, 4, 2),
            ('BIT4033', 'Elective IV', 3, 4, 2),
        ]

        subjects = {}
        for code, name, credits, year, semester in subject_data:
            subj, _ = Subject.objects.update_or_create(
                subject_code=code,
                defaults={
                    'subject_name': name,
                    'credit_hours': credits,
                    'programme': programme,
                    'year': year,
                    'semester': semester,
                },
            )
            subjects[code] = subj

        self.stdout.write(f'  Created {len(subjects)} subjects')
        return subjects

    def _create_prerequisites(self, subjects):
        prerequisite_pairs = [
            # Year 1 Sem 2 prerequisites
            ('BCS1033', 'BCS1023'),  # Data Structures requires Programming Fundamentals
            ('BCS1043', 'BCS1023'),  # OOP requires Programming Fundamentals
            ('BIT1043', 'BCS1013'),  # Database Systems requires Intro to CS
            ('BEN1023', 'BEN1013'),  # English II requires English I

            # Year 2 Sem 1 prerequisites
            ('BCS2013', 'BCS1043'),  # Software Engineering requires OOP
            ('BCS2023', 'BCS1043'),  # Web Programming requires OOP
            ('BCS2023', 'BIT1043'),  # Web Programming requires Database Systems
            ('BIT2013', 'BIT1023'),  # Operating Systems requires Computer Organization
            ('BIT2023', 'BIT1023'),  # Computer Networks requires Computer Organization
            ('BCS2033', 'BCS1043'),  # HCI requires OOP

            # Year 2 Sem 2 prerequisites
            ('BCS2043', 'BCS2013'),  # Requirements Engineering requires Software Engineering
            ('BCS2053', 'BCS2023'),  # Mobile App Dev requires Web Programming
            ('BCS2063', 'BCS2013'),  # Software Design requires Software Engineering
            ('BIT2043', 'BIT2023'),  # Info Security requires Computer Networks
            ('BIT2053', 'BIT1043'),  # System Analysis requires Database Systems

            # Year 3 Sem 1 prerequisites
            ('BCS3013', 'BCS2013'),  # Software Testing requires Software Engineering
            ('BCS3013', 'BCS2063'),  # Software Testing requires Software Design
            ('BCS3023', 'BCS2013'),  # Project Management requires Software Engineering
            ('BCS3033', 'BCS1033'),  # AI requires Data Structures
            ('BCS3043', 'BIT2013'),  # Cloud Computing requires Operating Systems
            ('BCS3043', 'BIT2023'),  # Cloud Computing requires Computer Networks

            # Year 3 Sem 2 prerequisites
            ('BIT3043', 'BCS3013'),  # Project 1 requires Software Testing
            ('BIT3043', 'BCS3023'),  # Project 1 requires Project Management
            ('BCS3053', 'BCS3013'),  # DevOps requires Software Testing
            ('BCS3063', 'BIT1043'),  # Data Science requires Database Systems
            ('BCS3063', 'BIT2033'),  # Data Science requires Statistics
            ('BCS3073', 'BIT1043'),  # Advanced DB requires Database Systems

            # Year 4 prerequisites
            ('BIT4016', 'BIT3043'),  # Industrial Training requires Project 1
            ('BIT4026', 'BIT4016'),  # Project 2 requires Industrial Training
        ]

        count = 0
        for subj_code, prereq_code in prerequisite_pairs:
            if subj_code in subjects and prereq_code in subjects:
                Prerequisite.objects.update_or_create(
                    subject=subjects[subj_code],
                    prerequisite_subject=subjects[prereq_code],
                )
                count += 1

        self.stdout.write(f'  Created {count} prerequisite relationships')

    def _create_rules(self, programme):
        rules = [
            ('max_credits', 21),
            ('probation_cap', 12),
            ('min_credits', 3),
            ('max_repeat', 3),
        ]

        for rule_type, value in rules:
            Rule.objects.update_or_create(
                rule_type=rule_type,
                programme=programme,
                defaults={'rule_value': value, 'is_active': True},
            )

        self.stdout.write(f'  Created {len(rules)} rules')

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
            self.stdout.write('  Created admin user: ADMIN001 / ADMIN001')
        else:
            self.stdout.write('  Admin user already exists')

    def _create_sample_students(self, programme):
        sample_students = [
            {
                'student_id': '202209020001',
                'full_name': 'Ahmad Bin Hassan',
                'ic_passport': '010515140001',
                'year': 1, 'semester': 1,
                'status': 'active',
            },
            {
                'student_id': '202209020002',
                'full_name': 'Nuru Rashid Matora',
                'ic_passport': '020320140002',
                'year': 3, 'semester': 2,
                'status': 'active',
            },
            {
                'student_id': '202209020003',
                'full_name': 'Siti Aminah Binti Yusof',
                'ic_passport': '030812140003',
                'year': 2, 'semester': 1,
                'status': 'active',
            },
            {
                'student_id': '202209020004',
                'full_name': 'David Tan Wei Ming',
                'ic_passport': '040101140004',
                'year': 2, 'semester': 2,
                'status': 'probation',
            },
            {
                'student_id': '202209020005',
                'full_name': 'Priya Devi A/P Ramasamy',
                'ic_passport': '050630140005',
                'year': 1, 'semester': 2,
                'status': 'active',
            },
        ]

        for s in sample_students:
            user, created = User.objects.get_or_create(
                student_id=s['student_id'],
                defaults={
                    'full_name': s['full_name'],
                    'ic_passport': s['ic_passport'],
                    'role': 'student',
                },
            )
            if created:
                user.set_password(s['ic_passport'])
                user.save()

            Student.objects.update_or_create(
                user=user,
                defaults={
                    'programme': programme,
                    'current_year': s['year'],
                    'current_semester': s['semester'],
                    'status': s['status'],
                },
            )

        self.stdout.write(f'  Created {len(sample_students)} sample students')

        self._create_sample_enrolments(programme)

    def _create_sample_enrolments(self, programme):
        from core.models import Enrolment

        try:
            nuru = User.objects.get(student_id='202209020002').student_profile
        except (User.DoesNotExist, Student.DoesNotExist):
            return

        y1s1_codes = ['BCS1013', 'BCS1023', 'BIT1013', 'BIT1023', 'MPU3113', 'MPU3123', 'BEN1013']
        y1s2_codes = ['BCS1033', 'BCS1043', 'BIT1033', 'BIT1043', 'BEN1023', 'MPU3133', 'MPU3212']
        y2s1_codes = ['BCS2013', 'BCS2023', 'BIT2013', 'BIT2023', 'BIT2033', 'BCS2033', 'MPU3143']
        y2s2_codes = ['BCS2043', 'BCS2053', 'BCS2063', 'BIT2043', 'BIT2053', 'BEN2013', 'BCS2072']
        y3s1_codes = ['BCS3013', 'BCS3023', 'BCS3033', 'BCS3043', 'BIT3013', 'BIT3023', 'BIT3033']

        passed_semesters = [
            ('202201', y1s1_codes),
            ('202202', y1s2_codes),
            ('202301', y2s1_codes),
            ('202302', y2s2_codes),
            ('202401', y3s1_codes),
        ]

        for sem, codes in passed_semesters:
            for code in codes:
                try:
                    subject = Subject.objects.get(subject_code=code)
                    Enrolment.objects.get_or_create(
                        student=nuru,
                        subject=subject,
                        semester=sem,
                        defaults={'status': 'passed', 'grade': 'B+'},
                    )
                except Subject.DoesNotExist:
                    pass

        try:
            siti = User.objects.get(student_id='202209020003').student_profile
            for code in y1s1_codes:
                try:
                    subject = Subject.objects.get(subject_code=code)
                    Enrolment.objects.get_or_create(
                        student=siti,
                        subject=subject,
                        semester='202201',
                        defaults={'status': 'passed', 'grade': 'A-'},
                    )
                except Subject.DoesNotExist:
                    pass

            for code in y1s2_codes:
                try:
                    subject = Subject.objects.get(subject_code=code)
                    Enrolment.objects.get_or_create(
                        student=siti,
                        subject=subject,
                        semester='202202',
                        defaults={'status': 'passed', 'grade': 'B'},
                    )
                except Subject.DoesNotExist:
                    pass
        except (User.DoesNotExist, Student.DoesNotExist):
            pass

        try:
            priya = User.objects.get(student_id='202209020005').student_profile
            for code in y1s1_codes:
                try:
                    subject = Subject.objects.get(subject_code=code)
                    Enrolment.objects.get_or_create(
                        student=priya,
                        subject=subject,
                        semester='202201',
                        defaults={'status': 'passed', 'grade': 'B'},
                    )
                except Subject.DoesNotExist:
                    pass
        except (User.DoesNotExist, Student.DoesNotExist):
            pass

        try:
            david = User.objects.get(student_id='202209020004').student_profile
            for code in y1s1_codes:
                try:
                    subject = Subject.objects.get(subject_code=code)
                    grade = 'F' if code == 'BCS1023' else 'C'
                    status_val = 'failed' if code == 'BCS1023' else 'passed'
                    Enrolment.objects.get_or_create(
                        student=david,
                        subject=subject,
                        semester='202201',
                        defaults={'status': status_val, 'grade': grade},
                    )
                except Subject.DoesNotExist:
                    pass

            for code in y1s2_codes:
                try:
                    subject = Subject.objects.get(subject_code=code)
                    grade = 'D' if code in ('BCS1033', 'BCS1043') else 'C+'
                    status_val = 'failed' if code in ('BCS1033', 'BCS1043') else 'passed'
                    Enrolment.objects.get_or_create(
                        student=david,
                        subject=subject,
                        semester='202202',
                        defaults={'status': status_val, 'grade': grade},
                    )
                except Subject.DoesNotExist:
                    pass

            for code in y2s1_codes:
                try:
                    subject = Subject.objects.get(subject_code=code)
                    Enrolment.objects.get_or_create(
                        student=david,
                        subject=subject,
                        semester='202301',
                        defaults={'status': 'passed', 'grade': 'C'},
                    )
                except Subject.DoesNotExist:
                    pass
        except (User.DoesNotExist, Student.DoesNotExist):
            pass

        self.stdout.write('  Created sample enrolment history')
