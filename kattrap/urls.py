from django.urls import path

from .views import (
    DailyGiftClaimView,
    DailyGiftStatusView,
    DecorPurchaseView,
    DecorSellView,
    DecorStoreView,
    EquipItemView,
    EquippedView,
    PurchaseView,
    RoundSubmitView,
    SellView,
    StoreView,
    UnequipView,
    WalletsView,
)

urlpatterns = [
    path('wallets/', WalletsView.as_view(), name='wallets'),
    path('store/<str:character>/', StoreView.as_view(), name='store'),
    path('store/<str:character>/purchase/', PurchaseView.as_view(), name='purchase'),
    path('store/<str:character>/sell/', SellView.as_view(), name='sell'),
    path('store/<str:character>/equip/', EquipItemView.as_view(), name='equip'),
    path('store/<str:character>/unequip/', UnequipView.as_view(), name='unequip'),
    path('equipped/<str:character>/', EquippedView.as_view(), name='equipped'),
    # Pet Shop Boys - the shared decor catalog, not under store/<character>/
    # since a decor item isn't any one character's (see StoreItem.character
    # and DecorStoreView's own docstring).
    path('decor/', DecorStoreView.as_view(), name='decor-store'),
    path('decor/purchase/', DecorPurchaseView.as_view(), name='decor-purchase'),
    path('decor/sell/', DecorSellView.as_view(), name='decor-sell'),
    path('daily-gift/status/', DailyGiftStatusView.as_view(), name='daily-gift-status'),
    path('daily-gift/claim/', DailyGiftClaimView.as_view(), name='daily-gift-claim'),
    path('rounds/submit/', RoundSubmitView.as_view(), name='round-submit'),
]
