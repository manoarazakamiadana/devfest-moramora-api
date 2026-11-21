from django.utils import timezone

from authentication.models import IssuedAccessToken


def revoke_all_tokens_for_user(user):
    return IssuedAccessToken.objects.filter(
        user=user,
        revoked_at__isnull=True,
    ).update(revoked_at=timezone.now())
