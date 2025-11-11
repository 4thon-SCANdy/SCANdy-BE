from datetime import timedelta
from dateutil.relativedelta import relativedelta

from django.utils import timezone
from django.db import transaction
from django.conf import settings

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import SessionToken
from .services import make_token, hash_token, get_user_from_non_google_token

from apps.users.serializers import UserSerializer
from apps.users.models import User
from apps.users.services import create_jwt_token
from external.dummy_serializers import DummySerializer

from drf_spectacular.utils import extend_schema

# 구글 연동 안하는 사용자 회원가입.
class NonGoogleRegisterView(APIView):

    @extend_schema(request=DummySerializer)
    def post(self, request):
        response = Response({"message": "register success."})
        
        # 만약 이미 있는 사용자라면 기존 사용자를 삭제한다.
        try:
            user = get_user_from_non_google_token(request)
            
            if user:
                # atomic하게 삭제.
                with transaction.atomic():
                    user.delete()
                    
                # cookie를 삭제.        
                response.delete_cookie('non_google_token', path='/')
        except Exception as e:
            print("Exception in get_user_from_non_google_token block:", e)
            import traceback
            traceback.print_exc()  # 전체 트레이스백 출력
            user = None
        
        token = make_token()
        token_hash = hash_token(token)
        expires_at = timezone.now() + relativedelta(days=1)  # 1년으로 해도 되지만 우선 1시간으로 설정.
    
        # 구글 사용자 아닌 User를 새로 만듬.
        user: User = UserSerializer().create({"is_google_sync": False})
        user.save()
        
        SessionToken.objects.create(
            user=user,
            token_hash=token_hash,
            expires_at=expires_at
        )
        
        response.set_cookie(
            key='non_google_token',
            value=token,
            expires=expires_at,
            httponly=True,
            # samesite='Lax',
            secure=settings.COOKIE_SECURE,  # HTTP/S 관련 {로컬(False), 배포(True)
            samesite=settings.COOKIE_SAMESITE, # 크로스사이트 허용
            path='/',
        )

        return response
    

# 로그인 뷰
class NonGoogleLoginView(APIView):
    
    @extend_schema(request=DummySerializer)
    def post(self, request):
        user = get_user_from_non_google_token(request)
        jwt_token = create_jwt_token(user)
        
        return Response({"token": jwt_token ,"message": "login success"})
