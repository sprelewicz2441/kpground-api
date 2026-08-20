from django.urls import path

from .views import (
    DailyGiftClaimView,
    DailyGiftStatusView,
    PurchaseView,
    RoundSubmitView,
    StoreView,
    WalletsView,
)

urlpatterns = [
    path('wallets/', WalletsView.as_view(), name='wallets'),
    path('store/<str:character>/', StoreView.as_view(), name='store'),
    path('store/<str:character>/purchase/', PurchaseView.as_view(), name='purchase'),
    path('daily-gift/status/', DailyGiftStatusView.as_view(), name='daily-gift-status'),
    path('daily-gift/claim/', DailyGiftClaimView.as_view(), name='daily-gift-claim'),
    path('rounds/submit/', RoundSubmitView.as_view(), name='round-submit'),
]
