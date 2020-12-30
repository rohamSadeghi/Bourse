from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from django.utils.translation import ugettext_lazy as _


from .models import User, UserProfile


@admin.register(User)
class MyUserAdmin(UserAdmin):
    fieldsets = (
        (None, {'fields': ('first_name', 'last_name', 'phone_number', 'password')}),
        (_('Personal info'), {'fields': ()}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('first_name', 'last_name', 'phone_number', 'password1', 'password2'),
        }),
    )
    list_display = ('phone_number', 'first_name', 'last_name', 'is_staff')
    search_fields = ('phone_number', 'first_name', 'last_name')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    ordering = ('phone_number',)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_select_related = ['user', ]
    list_display = ['user', 'first_name', 'last_name']
    autocomplete_fields = ['user', ]
    search_fields = ['user__phone_number', 'first_name', 'last_name']
    actions = None

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False
