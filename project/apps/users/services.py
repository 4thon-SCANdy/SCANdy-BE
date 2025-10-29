from django.conf import settings
from django.http.request import HttpRequest

from google_auth_oauthlib.flow import InstalledAppFlow

# Scope.. 구글의 허용범위 지정.
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/calendar",
]
REDIRECT_CALLBACK_PATH = "auth/google/oauth_callback/"

# redirect URL 설정까지해서 Flow return.
def get_google_flow(request: HttpRequest) -> InstalledAppFlow:
    flow = InstalledAppFlow.from_client_secrets_file(
        settings.GOOGLE_OAUTH_JSON,
        scopes=SCOPES
    )

    scheme = "https" if request.is_secure() else "http"
    flow.redirect_uri = f"{scheme}://{request.get_host()}/{REDIRECT_CALLBACK_PATH}"
    return flow

