# django
from django.conf import settings

# rest_framework
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework.decorators import api_view

# google libs
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

@api_view(['GET'])
def google_auth_url(request: Request):

    # google flow 생성.
    # 에러 처리 필요.
    flow = InstalledAppFlow.from_client_secrets_file(
        settings.GOOGLE_OAUTH_JSON,
        scopes=SCOPES
    )

    auth_url, state = flow.authorization_url()

    # 세션에 state를 저장. 나중에 확인 필요.
    request.session['oauth_state'] = state


    return Response({"auth_url": auth_url})

