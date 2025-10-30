import jwt
from datetime import datetime, timedelta

from django.conf import settings
from django.http.request import HttpRequest

from google_auth_oauthlib.flow import InstalledAppFlow

# models
from .models import User

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

# jwt token 생성.
def create_jwt_token(user: User):
    payload = {
        "user_id": user.id,
        "exp": datetime.now() + timedelta(seconds=settings.JWT_EXP_DELTA_SECONDS),
        "iat": datetime.now(),
    }
    print(type(settings.JWT_SECRET_KEY))
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    print(token)
    return token

# jwt token -> user object
def get_user_from_token(token):
    try:
        payload: dict = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("user_id")
        user = User.objects.get(id=user_id)
        return user
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, User.DoesNotExist):
        return None