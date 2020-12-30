from django.db import models
from django.utils.translation import ugettext_lazy as _

from apps.commenting.models import AbstractComment, AbstractCommentVote


class Namad(models.Model):
    id = models.CharField(_('id'), primary_key=True, max_length=24, editable=False)
    created_time = models.DateTimeField(_('created time'), auto_now_add=True)
    updated_time = models.DateTimeField(_('updated time'), auto_now=True)
    title = models.CharField(_('title'), max_length=50)
    name = models.CharField(_('name'), max_length=16, unique=True)
    group_name = models.CharField(_('group name'), max_length=40)
    script = models.PositiveIntegerField(_('namad script'), blank=True, null=True)
    description = models.TextField(_('description'), blank=True)
    market = models.CharField(_("market"), max_length=50)
    is_allowed = models.BooleanField(_('is allowed'), default=True, editable=False)
    is_enable = models.BooleanField(_('is enable'), default=True)

    class Meta:
        verbose_name = _("Namad")
        verbose_name_plural = _("Namads")

    def __str__(self):
        return self.name


class NamadComment(AbstractComment):
    namad = models.ForeignKey('Namad', verbose_name=_('namad'), related_name='comments', on_delete=models.CASCADE)

    class Meta:
        verbose_name = _("Namad comment")
        verbose_name_plural = _("Namad comments")

    def __str__(self):
        return f"user: {str(self.user)}->namad: {str(self.namad)}"


class NamadCommentVote(AbstractCommentVote):
    comment = models.ForeignKey("NamadComment", on_delete=models.CASCADE, related_name="votes", verbose_name=_("comment"))

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['comment', 'user'], name='namad_user_comment_vote')
        ]
        verbose_name = _("Comment vote")
        verbose_name_plural = _("Comment votes")

    def __str__(self):
        return f"comment: {str(self.comment)}->vote: {str(self.vote)}"
