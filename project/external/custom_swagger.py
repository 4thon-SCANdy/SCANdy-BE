from drf_spectacular.utils import OpenApiParameter

TOKEN_HEADER = OpenApiParameter(
    name='token',
    location=OpenApiParameter.HEADER,
    required=True,
    description="예시: `Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`"
)