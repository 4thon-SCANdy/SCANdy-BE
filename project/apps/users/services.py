import jwt
from datetime import datetime, timedelta, timezone

from django.conf import settings
from django.http.request import HttpRequest

from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions

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
        "exp": datetime.now(timezone.utc) + timedelta(seconds=settings.JWT_EXP_DELTA_SECONDS),
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token

# jwt token -> user object
def get_user_from_token(token):
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("user_id")
        user = User.objects.get(id=user_id)
        return user
    except jwt.ExpiredSignatureError:
        print("Error: Token has expired")
        return None
    except jwt.InvalidTokenError:
        print("Error: Invalid token")
        return None
    except User.DoesNotExist:
        print(f"Error: User with id {user_id} does not exist")
        return None

# user 인증 클래스. 계속해서 사용해야 함.
class JWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get('token')
        if not auth_header:
            return None

        try:
            token_type, token = auth_header.split()
            if token_type.lower() != 'bearer':
                return None
        except ValueError:
            return None

        user = get_user_from_token(token)
        if user is None:
            raise exceptions.AuthenticationFailed('Invalid or expired token')

        return (user, token)