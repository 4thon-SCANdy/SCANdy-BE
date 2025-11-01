from datetime import timedelta
from dateutil.relativedelta import relativedelta

from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import SessionToken
from .services import make_token, hash_token, get_user_from_non_google_token

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
            samesite='Lax',
            path='/',
        )

        return response
    

# 로그인 뷰
class NonGoogleLoginView(APIView):
    def post(self, request):
        user = get_user_from_non_google_token(request)
        jwt_token = create_jwt_token(user)
        
        return Response({"token": jwt_token ,"message": "login success"})
