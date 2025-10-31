import secrets, hashlib

# 토큰 생성.
def make_token(n_bytes=48):
    return secrets.token_urlsafe(n_bytes)

# 토큰 해시하기.
def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()



