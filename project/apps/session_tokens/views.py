from datetime import timedelta
from dateutil.relativedelta import relativedelta

from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import SessionToken
from .sevices import make_token, hash_token

from apps.users.serializers import UserSerializer
from apps.users.models import User
from apps.users.services import create_jwt_token

# 구글 연동 안하는 사용자 회원가입.
class NonGoogleRegisterView(APIView):
    def post(self, request):
        token = make_token()
        token_hash = hash_token(token)
        expires_at = timezone.now() + relativedelta(hours=1)  # 1년으로 해도 되지만 우선 1시간으로 설정.
    
        # 구글 사용자 아닌 User를 새로 만듬.
        user: User = UserSerializer().create({"is_google_sync": False})
        user.save()
        
        SessionToken.objects.create(
            user=user,
            token_hash=token_hash,
            expires_at=expires_at
        )
        
        response = Response({"message": "register success."})
        response.set_cookie(
            key='non_google_token',
            value=token,
            expires=expires_at,
            httponly=True,
            samesite='Strict',
            path='/',
        )

        return response
    

# 로그인 뷰
class NonGoogleLoginView(APIView):
    def post(self, request):
        # 토큰 우선순위: 쿠키 -> 요청 바디
        non_google_token = request.COOKIES.get('non_google_token')
        if not non_google_token:
            return Response({"detail": "no token."}, status=status.HTTP_400_BAD_REQUEST)

        token_hash = hash_token(non_google_token)
        now = timezone.now()

        session = (
            SessionToken.objects
            .select_related('user')
            .filter(token_hash=token_hash, expires_at__gt=now)
            .first()
        )

        if not session:
            return Response({"detail": "invalid or expired token."}, status=status.HTTP_401_UNAUTHORIZED)

        user = session.user
        jwt_token = create_jwt_token(user)
        
        return Response({"token": jwt_token ,"message": "login success"})
