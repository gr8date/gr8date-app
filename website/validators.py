import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class ComplexPasswordValidator:
    """
    Enforce strong passwords:
    - at least 10 characters
    - at least one uppercase letter
    - at least one lowercase letter
    - at least one digit
    - at least one symbol (non alphanumeric)
    """

    def validate(self, password, user=None):
        if len(password) < 10:
            raise ValidationError(
                _("This password is too short. It must contain at least 10 characters."),
                code='password_too_short',
            )

        if not re.search(r'[A-Z]', password):
            raise ValidationError(
                _("This password must contain at least one uppercase letter."),
                code='password_no_upper',
            )

        if not re.search(r'[a-z]', password):
            raise ValidationError(
                _("This password must contain at least one lowercase letter."),
                code='password_no_lower',
            )

        if not re.search(r'\d', password):
            raise ValidationError(
                _("This password must contain at least one digit."),
                code='password_no_digit',
            )

        if not re.search(r'[^A-Za-z0-9]', password):
            raise ValidationError(
                _("This password must contain at least one symbol (e.g. !@#$%&*)."),
                code='password_no_symbol',
            )

    def get_help_text(self):
        return _(
            "Your password must be at least 10 characters long and contain at least one "
            "uppercase letter, one lowercase letter, one digit, and one symbol."
        )

