"""앱 전역 커스텀 예외.

서비스 레이어에서 raise → 라우터/exception handler에서 HTTP 상태코드 매핑.
"""


class AppError(Exception):
    """기본 앱 예외."""
    pass


class NotFoundError(AppError):
    """리소스를 찾을 수 없음 (404)."""
    pass


class BusinessRuleError(AppError):
    """비즈니스 규칙 위반 (403/409 등)."""

    def __init__(self, message: str, *, status_code: int = 403):
        super().__init__(message)
        self.status_code = status_code


class DuplicateError(AppError):
    """중복 리소스 (409)."""
    pass


class UnauthorizedError(AppError):
    """인증 실패 (401)."""
    pass


class PermissionDeniedError(AppError):
    """권한 부족 (403)."""
    pass


class ValidationError(AppError):
    """입력 검증 오류 (422)."""

    def __init__(self, errors: list[str], *, details: list[dict] | None = None):
        super().__init__("; ".join(errors))
        self.errors = errors
        self.details = details or []
