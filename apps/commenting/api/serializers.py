from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from apps.accounts.api.serializers import UserProfileSerializer
from apps.accounts.models import UserProfile


class BaseCommentSerializer(serializers.ModelSerializer):
    positive_votes_sum = serializers.IntegerField(read_only=True)
    negative_votes_sum = serializers.IntegerField(read_only=True)
    user_profile = serializers.SerializerMethodField()
    user_vote = serializers.SerializerMethodField()

    class Meta:
        model = None
        fields = [
            'id', 'user_profile', 'content',
            'positive_votes_sum', 'negative_votes_sum',
            'user_vote', 'created_time'
        ]
        read_only_fields = ['id', 'created_time', ]

    def get_user_vote(self, obj):
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            try:
                return obj.votes.get(user=request.user, comment=obj).vote
            except ObjectDoesNotExist:
                return 0
        return 0

    def get_user_profile(self, obj):
        try:
            profile = obj.user.profile
        except UserProfile.DoesNotExist:
            profile = None

        if profile:
            return UserProfileSerializer(
                profile,
                remove_fields=['gender', 'birth_date', 'email_address', 'has_password'],
                context={'request': self.context.get('request')}
            ).data


class BaseCommentVoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = None
        fields = ['id', 'vote', 'created_time']
        read_only_fields = ['id', 'created_time', ]

    def create(self, validated_data):
        model_class = self.Meta.model
        vote = validated_data.pop('vote')
        instance, _created = model_class.objects.update_or_create(
            **validated_data,
            defaults={'vote': vote}
        )
        return instance
