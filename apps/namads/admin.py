from django.contrib import admin

from apps.commenting.admin import BaseCommentAdmin
from apps.namads.models import Namad, NamadComment


@admin.register(Namad)
class NamadAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "group_name", "created_time", "is_enable")
    search_fields = ('id', 'name', 'group_name')
    list_filter = ['is_enable', ]


@admin.register(NamadComment)
class ArticleCommentAdmin(BaseCommentAdmin):
    list_display = ["user", "namad", "is_approved", "created_time", "is_enable"]
    search_fields = ('namad__name', )

    def get_list_display(self, request):
        list_display = super().get_list_display(request)
        list_display.append("namad")
        return list_display
