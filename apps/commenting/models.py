from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models.functions import Coalesce
from django.utils.translation import ugettext_lazy as _

from utils.utils import ApprovedManager, JalaliTimeMixin


class AbstractComment(models.Model, JalaliTimeMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._votes_data = None

    created_time = models.DateTimeField(_('created time'), auto_now_add=True)
    updated_time = models.DateTimeField(_('updated time'), auto_now=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('user'), related_name="%(class)s", on_delete=models.CASCADE)
    approved_user = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, editable=False, on_delete=models.CASCADE, related_name="approved_%(class)s", verbose_name=_("approved user"))
    approved_time = models.DateTimeField(_("approved time"), blank=True, null=True, editable=False)
    content = models.TextField(_('content'))
    is_enable = models.BooleanField(_("is enable"), default=True)

    objects = models.Manager()
    approves = ApprovedManager()

    class Meta:
        abstract = True

    # Following method and attribute is used in admin page for showing tick or cross
    def is_approved(self):
        return bool(self.approved_user)
    is_approved.boolean = True

    def get_votes_data(self):
        if self._votes_data is None:
            self._votes_data = self.votes.aggregate(
                total_pos=Coalesce(models.Sum(
                    models.Case(
                        models.When(vote__gt=0, then=models.F('vote')),
                        default=models.Value(0),
                        output_field=models.IntegerField()
                )), 0),
                total_neg=Coalesce(models.Sum(
                    models.Case(
                        models.When(vote__lt=0, then=models.F('vote')),
                        default=models.Value(0),
                        output_field=models.IntegerField()
                )), 0)
            )
        return self._votes_data

    def positive_votes_sum(self):
        votes_data = self.get_votes_data()
        return votes_data['total_pos']

    def negative_votes_sum(self):
        votes_data = self.get_votes_data()
        return abs(votes_data['total_neg'])


class AbstractCommentVote(models.Model):
    created_time = models.DateTimeField(_("created time"), auto_now_add=True)
    updated_time = models.DateTimeField(_("updated time"), auto_now=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="%(class)s", verbose_name=_("user"))
    vote = models.IntegerField(_("vote"), validators=[MinValueValidator(-1), MaxValueValidator(1)])

    class Meta:
        abstract = True
