from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower


class User(AbstractUser):
    email = models.EmailField("email address", unique=True)

    class Meta(AbstractUser.Meta):
        constraints = [
            models.UniqueConstraint(Lower("email"), name="auth_user_email_ci_unique"),
            models.UniqueConstraint(
                Lower("username"),
                name="auth_user_username_ci_unique",
            ),
        ]


class IssuedAccessToken(models.Model):
    jti = models.CharField(max_length=255, unique=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="issued_access_tokens",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "revoked_at"]),
        ]

    def __str__(self):
        return f"Access token for user {self.user_id}"
