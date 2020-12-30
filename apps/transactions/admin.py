from django.contrib import admin
from django.utils import timezone

from apps.transactions.models import Package, PurchasePackage


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'is_filter', 'is_article', 'is_enable']
    list_filter = ['is_filter', 'is_article', 'is_enable']
    search_fields = ['name',]


@admin.register(PurchasePackage)
class PurchasePackageAdmin(admin.ModelAdmin):
    list_display = ('user', 'package', 'is_paid', 'created_time')
    autocomplete_fields = ['user', 'package']
    list_select_related = ['user', 'package']
    list_filter = ['is_paid', 'package__name']
    list_per_page = 30
    search_fields = ['user__phone_number', ]
    readonly_fields = [
        'invoice_uuid', 'transaction_id', 'redirect_url',
        'price', 'is_paid', 'start_date', 'expire_date'
    ]

    def save_model(self, request, obj, form, change):
        obj.start_date = timezone.now().date()
        expire_date =  obj.start_date + obj.package.duration
        obj.expire_date = expire_date
        obj.is_paid = True
        super().save_model(request, obj, form, change)

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
