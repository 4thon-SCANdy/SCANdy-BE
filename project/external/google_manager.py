from django.conf import settings
from django.http.request import HttpRequest

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

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

    # 만약 debug라면 그대로, debug가 아니라면 redirect url사용.
    if settings.DEBUG:
        scheme = "https" if request.is_secure() else "http"
        flow.redirect_uri = f"{scheme}://{request.get_host()}/{REDIRECT_CALLBACK_PATH}"
    else:
        flow.redirect_uri = settings.GOOGLE_REDIRECT_URL
    print("구글 리다이렉트", flow.redirect_uri)
    return flow

# google token으로부터 creds를 가져온다.
# jwt authentication이 끝난걸 가정. 즉 request.user에 user가 있는 상태.
# is_google_sync에만 호출해야 한다.
def get_creds_from_google_token(request: HttpRequest) -> Credentials:
    creds = Credentials(
        token=request.session.get('google_access_token', None),
        refresh_token=request.user.google_refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_PASSWORD,
        scopes=SCOPES,
    )
    # access token이 없거나 기간이 초기화 되었다면, 새로 refresh한다.
    if not creds or not creds.valid:
        creds.refresh(Request())
        request.session['google_access_token'] = creds.token

    return creds

