from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from oauth2_provider.models import AccessToken, Application, RefreshToken
from oauthlib.common import generate_token
from oauth2_provider.settings import oauth2_settings
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .constants import KATHRYN_USERNAME, KATTRAP_CLIENT_ID

User = get_user_model()


def _issue_token_response(user, application):
    """Mints a fresh access+refresh token pair for a user, in the same
    shape django-oauth-toolkit's own /o/token/ endpoint returns (used by
    the regular password-grant Login flow), so the frontend can treat
    every login path identically regardless of how the token was obtained.
    """
    expires = timezone.now() + timedelta(seconds=oauth2_settings.ACCESS_TOKEN_EXPIRE_SECONDS)
    access_token = AccessToken.objects.create(
        user=user,
        application=application,
        token=generate_token(),
        expires=expires,
        scope='read write',
    )
    refresh_token = RefreshToken.objects.create(
        user=user,
        application=application,
        token=generate_token(),
        access_token=access_token,
    )
    return Response(
        {
            'access_token': access_token.token,
            'refresh_token': refresh_token.token,
            'token_type': 'Bearer',
            'expires_in': oauth2_settings.ACCESS_TOKEN_EXPIRE_SECONDS,
            'scope': access_token.scope,
        }
    )


class KathrynQuickLoginView(APIView):
    """No-password login for a single known seeded account.

    Gated on ENABLE_KATHRYN_QUICKLOGIN so it's a one-line flip to disable
    later - everything downstream of this (wallets, store, gifts) uses the
    exact same token-authenticated endpoints as a normal login, only the
    login step itself is skipped.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        if not settings.ENABLE_KATHRYN_QUICKLOGIN:
            return Response({'detail': 'Quick login is disabled.'}, status=404)

        try:
            user = User.objects.get(username=KATHRYN_USERNAME)
        except User.DoesNotExist:
            return Response({'detail': 'Kathryn account is not set up yet.'}, status=503)

        try:
            application = Application.objects.get(client_id=KATTRAP_CLIENT_ID)
        except Application.DoesNotExist:
            return Response({'detail': 'KatTrap OAuth application is not set up yet.'}, status=503)

        return _issue_token_response(user, application)


class MeView(APIView):
    """Minimal authenticated identity check - lets the frontend (or a
    curl/test) confirm a token actually works without needing any of the
    kattrap economy endpoints built yet."""

    def get(self, request):
        return Response({'id': request.user.id, 'username': request.user.username})
