from django.utils.translation import ugettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound

from rest_framework.generics import CreateAPIView
from rest_framework.mixins import CreateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.views import TokenViewBase

from apps.accounts.api.serializers import (
    TokenObtainLifetimeSerializer,
    TokenRefreshLifetimeSerializer,
    UserRegistrationSerializer,
    SetPasswordSerializer,
    ChangePasswordSerializer,
    ForgetPasswordSerializer,
    UserProfileSerializer)
from apps.accounts.models import User, UserProfile
from apps.accounts.api.throttles import PhoneNumberScopedRateThrottle


class TokenObtainPairView(TokenViewBase):
    """
        Return JWT tokens (access and refresh) for specific user based on username and password.
    """
    serializer_class = TokenObtainLifetimeSerializer


class TokenRefreshView(TokenViewBase):
    """
        Renew tokens (access and refresh) with new expire time based on specific user's access token.
    """
    serializer_class = TokenRefreshLifetimeSerializer


class RegisterAPIView(CreateAPIView):
    """
    post:
        API view that creates a new user and sends verification sms.

    """
    serializer_class = UserRegistrationSerializer
    queryset = User.objects.all()
    throttle_classes = (PhoneNumberScopedRateThrottle,)
    throttle_scope = 'register'


class ProfileViewSet(CreateModelMixin,
                     GenericViewSet):
    """
        Create or update  user's profile.

            body:
              {
                "first_name": "string",
                "last_name": "string",
                "avatar": "string" -> image file,
                "gender": "null boolean" true-> male, false -> female, null -> unset,
                "birth_date": "string", example: 1989-01-01,
                "email_address": "string" -> valid email string
                }
    """
    serializer_class = UserProfileSerializer
    queryset = UserProfile.objects.all()
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    @action(detail=False, url_path='my-profile')
    def my_profile(self, request, *args, **kwargs):
        """
        Return specific user's profile.

        """
        user = request.user
        profile, _created = UserProfile.objects.get_or_create(user=user)
        serializer = self.get_serializer_class()
        context = self.get_serializer_context()
        return Response(serializer(instance=profile, context=context).data)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, url_path='delete-avatar', methods=['delete'])
    def delete_avatar(self, request, *args, **kwargs):
        """
            Delete  user's profile avatar.

        """
        try:
            profile = self.request.user.profile
        except UserProfile.DoesNotExist:
            raise NotFound(_("Requested profile does not exist"))
        profile.avatar = ""
        profile.save()
        return Response({"detail": _("Avatar image deleted successfully")}, status=status.HTTP_204_NO_CONTENT)


class SetPasswordAPIView(APIView):
    """
    post:
        API view that sets a new password for user.

            body:
                new_password: string
                confirm_password: string
    """
    serializer_class = SetPasswordSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        user = self.request.user
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=user)
        return Response({"detail": _("Your password was set successfully.")})


class ChangePasswordAPIView(APIView):
    """
    post:
        API view that changes password for user.

            body:
                old_password: string
                new_password: string
                confirm_password: string
    """
    serializer_class = ChangePasswordSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        user = self.request.user
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=user)
        return Response({"detail": _("Your password was set successfully.")})


class ForgetPasswordAPIView(APIView):
    """
    post:
        API view for requesting new verification code for users that has forgotten their passwords.

            body:
                phone_number: string
    """
    serializer_class = ForgetPasswordSerializer
    throttle_classes = (PhoneNumberScopedRateThrottle,)
    throttle_scope = 'register'

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response({"detail": _("Verification code has been successfully sent.")})
