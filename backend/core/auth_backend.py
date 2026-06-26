from django.contrib.auth.backends import BaseBackend
from core.models import User


class StudentIDBackend(BaseBackend):
    """
    Authenticates using Student ID + IC/Passport number.
    The IC/Passport number is stored hashed via set_password.
    """

    def authenticate(self, request, student_id=None, ic_passport=None, **kwargs):
        try:
            user = User.objects.get(student_id=student_id)
        except User.DoesNotExist:
            return None

        if user.check_password(ic_passport):
            return user
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
