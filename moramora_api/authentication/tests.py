from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from authentication.models import IssuedAccessToken
from authentication.services import revoke_all_tokens_for_user
from authentication.tokens import UnlimitedAccessToken

User = get_user_model()


class AuthenticationApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.password = "A-secure-password-381!"
        self.user = User.objects.create_user(
            username="example",
            email="example@example.com",
            password=self.password,
        )

    def signup(self, **overrides):
        data = {
            "username": "new-user",
            "email": "new@example.com",
            "password": "Another-secure-password-529!",
            "password_confirmation": "Another-secure-password-529!",
        }
        data.update(overrides)
        return self.client.post("/api/auth/signup/", data, format="json")

    def login(self):
        return self.client.post(
            "/api/auth/login/",
            {"email": self.user.email, "password": self.password},
            format="json",
        )

    def test_signup_creates_user_with_hashed_password(self):
        response = self.signup()

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["success"])
        created_user = User.objects.get(username="new-user")
        self.assertNotEqual(created_user.password, "Another-secure-password-529!")
        self.assertTrue(created_user.check_password("Another-secure-password-529!"))
        self.assertNotIn("password", response.data["data"])

    def test_signup_rejects_duplicate_username_and_email(self):
        duplicate_username = self.signup(username="EXAMPLE")
        duplicate_email = self.signup(email="EXAMPLE@example.com")

        self.assertEqual(duplicate_username.status_code, 400)
        self.assertEqual(duplicate_email.status_code, 400)

    def test_signup_rejects_invalid_username_and_passwords(self):
        invalid_username = self.signup(username="not a valid username!")
        mismatch = self.signup(password_confirmation="not-the-same")
        weak_password = self.signup(
            username="weak-user",
            password="password",
            password_confirmation="password",
        )

        self.assertEqual(invalid_username.status_code, 400)
        self.assertEqual(mismatch.status_code, 400)
        self.assertEqual(weak_password.status_code, 400)

    def test_login_returns_unexpiring_access_token(self):
        response = self.login()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["user"]["email"], self.user.email)
        token = UnlimitedAccessToken(response.data["data"]["access"])
        self.assertNotIn("exp", token.payload)
        self.assertTrue(
            IssuedAccessToken.objects.filter(
                jti=token["jti"],
                user=self.user,
                revoked_at__isnull=True,
            ).exists()
        )

    def test_login_rejects_invalid_credentials_and_inactive_accounts(self):
        invalid = self.client.post(
            "/api/auth/login/",
            {"email": self.user.email, "password": "incorrect"},
            format="json",
        )
        self.user.is_active = False
        self.user.save(update_fields=("is_active",))
        inactive = self.login()

        self.assertEqual(invalid.status_code, 401)
        self.assertEqual(inactive.status_code, 401)

    def test_login_is_rate_limited(self):
        for _ in range(5):
            self.assertEqual(self.login().status_code, 200)

        limited_response = self.login()

        self.assertEqual(limited_response.status_code, 429)
        self.assertFalse(limited_response.data["success"])

    def test_logout_revokes_token_and_prevents_reuse(self):
        login_response = self.login()
        token = login_response.data["data"]["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        logout_response = self.client.post("/api/auth/logout/", {}, format="json")
        profile_response = self.client.get("/api/auth/profile/")

        self.assertEqual(logout_response.status_code, 200)
        self.assertTrue(logout_response.data["success"])
        self.assertEqual(profile_response.status_code, 401)
        self.assertIsNotNone(
            IssuedAccessToken.objects.get(user=self.user).revoked_at
        )

    def test_profile_requires_authentication_and_returns_allowed_fields(self):
        anonymous_response = self.client.get("/api/auth/profile/")
        login_response = self.login()
        token = login_response.data["data"]["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        profile_response = self.client.get("/api/auth/profile/")

        self.assertEqual(anonymous_response.status_code, 401)
        self.assertEqual(profile_response.status_code, 200)
        self.assertEqual(
            set(profile_response.data["data"]),
            {"id", "username", "email", "date_joined", "last_login"},
        )
        self.assertNotIn("password", profile_response.data["data"])

    def test_all_user_tokens_can_be_revoked(self):
        first_token = self.login().data["data"]["access"]
        second_token = self.login().data["data"]["access"]
        self.assertEqual(revoke_all_tokens_for_user(self.user), 2)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {first_token}")
        response = self.client.get("/api/auth/profile/")

        self.assertEqual(response.status_code, 401)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {second_token}")
        second_response = self.client.get("/api/auth/profile/")
        self.assertEqual(second_response.status_code, 401)
