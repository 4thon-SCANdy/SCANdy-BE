# django
from django.conf import settings
from django.http.request import HttpRequest
from django.db import transaction

# rest_framework
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework import status

# google libs
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2 import id_token
from google.auth.transport import requests as google_request

# externals
from apps.session_tokens.services import get_user_from_non_google_token
from apps.google_calendar.services import update_google_calendar

from external.google_manager import get_google_flow

from .models import User
from .services import create_jwt_token, get_user_from_token
from .serializers import UserSerializer

@api_view(['GET'])
def google_auth_url(request: HttpRequest):
    # google flow 생성.
    flow = get_google_flow(request)

    # authorization url 받기.
    auth_url, state = flow.authorization_url(
        access_type='offline',
        prompt='consent',
    )

    # 세션에 state를 저장. 나중에 확인 필요.
    request.session['oauth_state'] = state

    return Response({"auth_url": auth_url})

@api_view(['GET'])
def google_oauth_callback(request: HttpRequest):
    # google로부터 code와 state를 받음.
    code = request.GET.get('code')
    state = request.GET.get('state')

    # 세션에 저장된 state가 다르면 error 반환.
    if state != request.session.get('oauth_state'):
        return Response({"error": "state is invalid"}, status=status.HTTP_400_BAD_REQUEST)
    
    # flow 생성.
    flow = get_google_flow(request)

    # code로 token을 생성.
    flow.fetch_token(code=code)
    creds = flow.credentials

    # 토큰 받기.
    access_token = creds.token
    refresh_token = getattr(creds, "refresh_token", None)
    id_token_jwt = getattr(creds, "id_token", None)

    # google id_info 받기.
    request_adapter = google_request.Request()
    id_info = id_token.verify_oauth2_token(
        id_token_jwt,
        request_adapter,
        settings.GOOGLE_CLIENT_ID,
    )
    
    # 만약 쿠키에 non_google_token이 있다면 user가 구글 연동인지 확인 후 진행.
    # 없으면 에러가 발생하기에 try catch를 해줘야 함.
    # 또한, 구글 연동을 하려고 하는데 이미 있다면 user를 바꿔서 처리해야 함.
    
    # 쿠키 관리를 위해 response 객체를 생성.
    response: Response = Response()
    
    try:
        user: User = get_user_from_non_google_token(request)
        
        # 만약 이미 user가 있고, is_google_sync가 아니라면 새로 구글 연동 user로 업데이트함.
        if user and not user.is_google_sync:
            google_sub = id_info.get("sub")
            email = id_info.get("email")
            
            serializer = UserSerializer(
                user,
                data={
                    "email": email,
                    "google_sub": google_sub,
                    "is_google_sync": True,
                    "google_refresh_token": refresh_token
                },
            )
            
            serializer.is_valid(raise_exception=True)
            # 쿠키에 있는 토큰을 삭제하고, session_token을 제거한다.
            # atomic하게 삭제.
            with transaction.atomic():
                user.session.delete()
            # cookie를 삭제.        
            response.delete_cookie('non_google_token', path='/')
            
            user = serializer.save()
        # 이미 google_sync라면 일반 google_user validation으로 넘어간다.
        else:
            user = None
    except Exception as e:
        user = None
    
    if not user:
        user = User.get_or_create_google_user(id_info, refresh_token)

    if user:
        # user calendar를 업데이트 한다.
        update_google_calendar(user, creds)

    # 세션에 로그인 상태 저장, jwt 토큰 발급.
    jwt_token = create_jwt_token(user)
    request.session['google_access_token'] = access_token

    return Response({"token": jwt_token, "message": "login successful", "email": user.email})


class UserFromTokenView(APIView):
    def post(self, request):
        token = request.data.get("token")
        if not token:
            return Response({"error": "Token is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # 토큰에서 user 가져오기
        user = get_user_from_token(token)

        serializer = UserSerializer(user)
        return Response(serializer.data)