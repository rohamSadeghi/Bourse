from django.contrib import admin
from django.utils import timezone

from utils.utils import ApprovedListFilter


class BaseCommentAdmin(admin.ModelAdmin):
    list_display = ["user", "is_approved", "created_time", "is_enable"]
    search_fields = ('article__title', 'article__slug')
    list_filter = ('is_enable', ApprovedListFilter)
    actions = ['set_approved', 'set_unapproved']

    def set_approved(self, request, queryset):
        queryset.filter(
            approved_user__isnull=True
        ).update(
            approved_user=request.user,
            approved_time=timezone.now()
        )

    def set_unapproved(self, request, queryset):
        queryset.filter(
            approved_user__isnull=False
        ).update(
            approved_user=None,
            approved_time=None
        )
