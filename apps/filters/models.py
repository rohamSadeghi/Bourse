from django.db import models
from django.utils.translation import ugettext_lazy as _

from utils.utils import filter_category_directory_path


class FilterCategory(models.Model):
    created_time = models.DateTimeField(_('created time'), auto_now_add=True)
    updated_time = models.DateTimeField(_('updated time'), auto_now=True)
    title = models.CharField(_('title'), max_length=120)
    slug = models.SlugField(_('slug'), max_length=50, unique=True, allow_unicode=True)
    is_free = models.BooleanField(_('is free'), default=True)
    image = models.ImageField(_('image'), upload_to=filter_category_directory_path)
    is_enable = models.BooleanField(_('is enable'), default=True)

    class Meta:
        verbose_name = _("Filter category")
        verbose_name_plural = _("Filter categories")
        ordering = ['id', ]

    def filter_codes(self):
        return self.filters.values_list('filter_code', flat=True)

    def __str__(self):
        return self.title


class SignalFilter(models.Model):
    created_time = models.DateTimeField(_('created time'), auto_now_add=True)
    updated_time = models.DateTimeField(_('updated time'), auto_now=True)
    title = models.CharField(_('title'), max_length=120)
    filter_code = models.CharField(_('filter code'), max_length=50, unique=True)
    category = models.ForeignKey('FilterCategory', on_delete=models.CASCADE, null=True, related_name='filters')
    is_enable = models.BooleanField(_('is enable'), default=True)

    class Meta:
        verbose_name = _("Filter")
        verbose_name_plural = _("Filters")

    def __str__(self):
        return self.title
