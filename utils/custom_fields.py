import re

from django.db import models
from django.utils.functional import Promise

from utils.utils import number_converter
from utils.validators import validate_phone_number


class CustomBigIntegerField(models.BigIntegerField):
    def get_prep_value(self, value):
        """Perform preliminary non-db specific value checks and conversions."""
        if isinstance(value, Promise):
            value = value._proxy____cast()

        if value is None:
            return None
        # This part just added to handle any kind of phone number login (regex)
        try:
            phone_number_matches = re.findall(validate_phone_number.regex, str(value).translate(number_converter))
            phone_number_match = phone_number_matches[0]
            return int(phone_number_match)
        except:
            return None
