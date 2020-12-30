from rest_framework import serializers

from apps.filters.models import FilterCategory


class SignalFilterSerializer(serializers.Serializer):
    filter_code = serializers.CharField(write_only=True)
    signal_data = serializers.JSONField(write_only=True)

    class Meta:
        fields = ('filter_code', 'signal_data')


class FilterCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = FilterCategory
        fields = ('id', 'title', 'slug', 'image', 'is_free', 'filter_codes')
