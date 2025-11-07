import secrets, hashlib

from django.utils import timezone

from rest_framework.exceptions import AuthenticationFailed

from .models import SessionToken

# 토큰 생성.
def make_token(n_bytes=48):
    return secrets.token_urlsafe(n_bytes)

# 토큰 해시하기.
def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# request로부터 token을 받아 user를 리턴한다.
def get_user_from_non_google_token(request):
    non_google_token = request.COOKIES.get('non_google_token')

    if not non_google_token:
        raise AuthenticationFailed("no token provided")

    token_hash = hash_token(non_google_token)
    now = timezone.now()

    session = (
        SessionToken.objects
        .select_related('user')
        .filter(token_hash=token_hash, expires_at__gt=now)
        .first()
    )

    if not session:
        raise AuthenticationFailed("invalid or expired token")

    return session.user