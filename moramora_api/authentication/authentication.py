from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

from authentication.models import IssuedAccessToken


class RegisteredTokenAuthentication(JWTAuthentication):
    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None

        user, validated_token = result
        token_is_active = IssuedAccessToken.objects.filter(
            jti=validated_token.get("jti"),
            user=user,
            revoked_at__isnull=True,
        ).exists()
        if not token_is_active:
            raise AuthenticationFailed("Token is invalid or has been revoked.")

        return user, validated_token
