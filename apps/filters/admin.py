from django.contrib import admin

from apps.filters.models import SignalFilter, FilterCategory


@admin.register(FilterCategory)
class FilterCategoryAdmin(admin.ModelAdmin):
    list_display = ["title", "slug", "is_free", "is_enable", "created_time"]
    search_fields = ('title', 'slug', )
    list_filter = ['is_free', 'is_enable', ]
    prepopulated_fields = {"slug": ("title",)}


@admin.register(SignalFilter)
class FilterAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "filter_code", "is_enable", "created_time"]
    search_fields = ('title', 'filter_code')
    list_filter = ['is_enable', 'category']
    autocomplete_fields = ('category', )
    list_select_related = ['category', ]
