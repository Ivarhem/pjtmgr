"""인증 미들웨어: 미로그인 요청을 /login 으로 리다이렉트하거나 401 반환."""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse


def _with_root_path(request: Request, path: str) -> str:
    root_path = (request.scope.get("root_path") or "").rstrip("/")
    if not path.startswith("/"):
        path = "/" + path
    return f"{root_path}{path}" if root_path else path

from app.core.exceptions import UnauthorizedError

# 인증 없이 접근 가능한 경로
_PUBLIC_PREFIXES = ("/static",)
_PUBLIC_EXACT = {"/login", "/api/v1/auth/login", "/api/v1/health"}


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        root_path = (request.scope.get("root_path") or "").rstrip("/")
        normalized_path = path
        if root_path and normalized_path.startswith(root_path):
            normalized_path = normalized_path[len(root_path):] or "/"

        # 공개 경로 허용
        if normalized_path in _PUBLIC_EXACT or any(normalized_path.startswith(p) for p in _PUBLIC_PREFIXES):
            return await call_next(request)

        # 세션 확인
        user_id = request.session.get("user_id")
        if not user_id:
            if normalized_path.startswith("/api/"):
                raise UnauthorizedError("로그인이 필요합니다.")
            return RedirectResponse(url=_with_root_path(request, "/login"))

        # request.state에 user_id 설정 (페이지 라우터에서 사용)
        request.state.user_id = user_id

        return await call_next(request)
