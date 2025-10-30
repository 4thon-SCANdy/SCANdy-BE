# django
from django.conf import settings
from django.http.request import HttpRequest

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
from .models import User
from .services import get_google_flow, create_jwt_token

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

    # get user.
    user = User.get_or_create_google_user(id_info, refresh_token)

    # 세션에 로그인 상태 저장, jwt 토큰 발급.
    jwt_token = create_jwt_token(user)
    request.session['google_access_token'] = access_token

    return Response({"token": jwt_token, "message": "login successful", "email": user.email})


