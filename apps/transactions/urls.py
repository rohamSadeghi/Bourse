from django.urls import path

from apps.transactions.views import PaymentView

urlpatterns = [
    path('payment/done/', PaymentView.as_view(), name='payment-done'),
]
