import re

from django.core import validators
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _


def validate_lower_case(value):
    if not value.islower():
        raise ValidationError(
            _('%(value)s must be in lower case form'),
            params={'value': value},
        )

validate_phone_number = validators.RegexValidator(
    re.compile('9[0-4,9]\d{8}'),
    message=_("Phone number not valid or detectable"),
    code='invalid',
)


class MobileNumberValidator(validators.RegexValidator):
    regex = '^9[0-3,9]\d{8}$'
    message = _('Mobile number is not a valid 9xxxxxxxx number')
    code = 'invalid_mobile_number'


clean_mobile_number_validator = MobileNumberValidator()
