from django.urls import path

from .views import KathrynQuickLoginView, MeView

urlpatterns = [
    path('kathryn-quicklogin/', KathrynQuickLoginView.as_view(), name='kathryn-quicklogin'),
    path('me/', MeView.as_view(), name='me'),
]
