from django.db import migrations

# Historical semester codes were stamped as <year><01|02|03> (sequential),
# not the actual intake month convention: Semester 1 -> January (01),
# Semester 2 -> May (05), Semester 3 -> September (09).
SEMESTER_CODE_REMAP = {
    '202202': '202205', '202203': '202209',
    '202402': '202405', '202403': '202409',
    '202502': '202505', '202503': '202509',
    '202602': '202605',
}


def fix_semester_codes(apps, schema_editor):
    Enrolment = apps.get_model('core', 'Enrolment')
    AddDropRequest = apps.get_model('core', 'AddDropRequest')
    Timetable = apps.get_model('core', 'Timetable')

    for old, new in SEMESTER_CODE_REMAP.items():
        Enrolment.objects.filter(semester=old).update(semester=new)
        AddDropRequest.objects.filter(semester=old).update(semester=new)
        Timetable.objects.filter(semester=old).update(semester=new)


def reverse_semester_codes(apps, schema_editor):
    Enrolment = apps.get_model('core', 'Enrolment')
    AddDropRequest = apps.get_model('core', 'AddDropRequest')
    Timetable = apps.get_model('core', 'Timetable')

    for old, new in SEMESTER_CODE_REMAP.items():
        Enrolment.objects.filter(semester=new).update(semester=old)
        AddDropRequest.objects.filter(semester=new).update(semester=old)
        Timetable.objects.filter(semester=new).update(semester=old)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_flatten_semesters'),
    ]

    operations = [
        migrations.RunPython(fix_semester_codes, reverse_semester_codes),
    ]
