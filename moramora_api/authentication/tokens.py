from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import AccessToken


class UnlimitedAccessToken(AccessToken):
    def set_exp(self, claim="exp", from_time=None, lifetime=None):
        return

    def verify(self):
        if "exp" in self.payload:
            self.check_exp()

        if (
            api_settings.JTI_CLAIM is not None
            and api_settings.JTI_CLAIM not in self.payload
        ):
            raise TokenError("Token has no id")

        self.verify_token_type()
