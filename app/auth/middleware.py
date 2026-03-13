"""인증 미들웨어: 미로그인 요청을 /login 으로 리다이렉트하거나 401 반환."""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse

# 인증 없이 접근 가능한 경로
_PUBLIC_PREFIXES = ("/static",)
_PUBLIC_EXACT = {"/login", "/api/v1/auth/login"}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # 공개 경로 허용
        if path in _PUBLIC_EXACT or any(path.startswith(p) for p in _PUBLIC_PREFIXES):
            return await call_next(request)

        # 세션 확인
        user_id = request.session.get("user_id")
        if not user_id:
            if path.startswith("/api/"):
                return JSONResponse({"detail": "로그인이 필요합니다."}, status_code=401)
            return RedirectResponse(url="/login")

        return await call_next(request)
