from django.db import migrations, models

# BCSSE subjects that sat in "year 4" (overall semester 10-12) don't fit inside
# the new 9-semester structure; spread them across the final semesters instead.
SUBJECT_SEMESTER_OVERRIDES = {
    'BIT4016': 7,  # Industrial Training
    'BIT4026': 8,  # Project 2
    'BCS4013': 9,  # Emerging Technologies
    'BIT4033': 9,  # Elective IV
}


def flatten_semesters(apps, schema_editor):
    Programme = apps.get_model('core', 'Programme')
    Subject = apps.get_model('core', 'Subject')
    Student = apps.get_model('core', 'Student')

    for subject in Subject.objects.all():
        if subject.subject_code in SUBJECT_SEMESTER_OVERRIDES:
            subject.semester = SUBJECT_SEMESTER_OVERRIDES[subject.subject_code]
        else:
            subject.semester = (subject.year - 1) * 3 + subject.semester
        subject.save(update_fields=['semester'])

    for student in Student.objects.all():
        student.current_semester = (student.current_year - 1) * 3 + student.current_semester
        student.save(update_fields=['current_semester'])

    Programme.objects.exclude(programme_code='DCS').update(total_semesters=9)
    Programme.objects.filter(programme_code='DCS').update(total_semesters=7)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_student_photo'),
    ]

    operations = [
        migrations.RunPython(flatten_semesters, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='programme',
            name='total_semesters',
            field=models.IntegerField(default=9),
        ),
        migrations.RemoveField(
            model_name='subject',
            name='year',
        ),
        migrations.RemoveField(
            model_name='student',
            name='current_year',
        ),
        migrations.AlterModelOptions(
            name='subject',
            options={'ordering': ['semester', 'subject_code']},
        ),
    ]
