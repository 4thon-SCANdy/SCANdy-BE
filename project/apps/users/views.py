import secrets

from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework.decorators import api_view

@api_view(['GET'])
def google_auth_url(request: Request):
    # state 생성. 보안상 사용자를 재확인하기 위함.
    state = secrets.token_urlsafe(16)

    # 세션에 저장.
    request.session['oauth_state'] = state

    return Response({"state": request.session['oauth_state']})

