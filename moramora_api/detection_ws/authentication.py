from channels.db import aclose_old_connections, database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import TokenError

from authentication.models import IssuedAccessToken
from authentication.tokens import UnlimitedAccessToken


@database_sync_to_async
def _resolve_authenticated_user(token):
    user_model = get_user_model()
    try:
        user = user_model.objects.get(
            pk=token["user_id"],
            is_active=True,
        )
    except (KeyError, TypeError, ValueError, user_model.DoesNotExist):
        return None

    if not IssuedAccessToken.objects.filter(
        jti=token["jti"],
        user=user,
        revoked_at__isnull=True,
    ).exists():
        return None

    return user


def _get_authentication(scope):
    authorization_headers = [
        value
        for key, value in scope.get("headers", [])
        if key.lower() == b"authorization"
    ]
    if len(authorization_headers) > 1:
        return None, False
    if authorization_headers:
        try:
            scheme, token = authorization_headers[0].decode("ascii").split()
        except (UnicodeDecodeError, ValueError):
            return None, False
        return (token, False) if scheme.lower() == "bearer" else (None, False)

    protocols = scope.get("subprotocols", [])
    if len(protocols) == 2 and protocols[0] == "bearer":
        return protocols[1], True
    return None, False


class JWTAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        await aclose_old_connections()
        raw_token, auth_via_subprotocol = _get_authentication(scope)
        user = AnonymousUser()
        auth_token = None
        if raw_token:
            try:
                auth_token = UnlimitedAccessToken(raw_token)
                authenticated_user = await _resolve_authenticated_user(auth_token)
                if authenticated_user is not None:
                    user = authenticated_user
                else:
                    auth_token = None
            except (KeyError, TypeError, ValueError, TokenError):
                auth_token = None

        authenticated_scope = dict(scope)
        authenticated_scope["user"] = user
        authenticated_scope["auth"] = auth_token
        authenticated_scope["auth_via_subprotocol"] = auth_via_subprotocol
        await self.app(authenticated_scope, receive, send)
