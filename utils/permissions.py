from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import BasePermission
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed

from apps.filters.models import FilterCategory
from apps.transactions.models import PurchasePackage


def check_content_permission(request, obj):
    if not obj.is_free:
        try:
            auth_attrs = JWTAuthentication().authenticate(request)
        except InvalidToken:
            return HttpResponse(
                "<h1>401 Given token not valid for any token type.</h1>",
                status=status.HTTP_401_UNAUTHORIZED
            )
        except AuthenticationFailed:
            return HttpResponse(
                "<h1>401 User not found.</h1>",
                status=status.HTTP_401_UNAUTHORIZED
            )

        if auth_attrs:
            has_purchase = PurchasePackage.objects.filter(
                expire_date__gt=timezone.now().date(),
                package__is_article=True,
                is_paid=True,
                user=auth_attrs[0]
            ).exists()

            if has_purchase:
                return HttpResponse(obj.content)
        else:
            return HttpResponse(
                "<h1>401 Authentication credentials were not provided.</h1>",
                status=status.HTTP_401_UNAUTHORIZED
            )
        raise PermissionDenied
    else:
        return HttpResponse(obj.content)


class FilterPermission(BasePermission):
    def has_permission(self, request, view):
        # It has to be get instead of ['category_id']. Do not change it because it will ruin docs API.
        category_id = view.kwargs.get('category_id')

        # Following condition reason is to use this class for all views that need this permission,
        # because category id becomes arbitrary
        if category_id:
            category = get_object_or_404(FilterCategory, **{'pk': category_id})

            if category.is_free:
                return True

        has_package = False

        if request.user and request.user.is_authenticated:
            has_package = PurchasePackage.objects.filter(
                user=request.user,
                is_paid=True,
                expire_date__gt=timezone.now().date(),
                package__is_filter=True
            ).exists()
        return has_package
