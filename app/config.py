import os
import secrets

# 기본 홈 페이지 (/ 접속 시 리다이렉트 대상)
# 향후 보고서/통계 등 메뉴 추가 후 .env에서 변경 가능
# 예: DEFAULT_HOME=/reports
DEFAULT_HOME: str = os.getenv("DEFAULT_HOME", "/my-contracts")

ENV: str = os.getenv("ENV", "dev")


def _resolve_session_secret_key() -> str:
    key = os.getenv("SESSION_SECRET_KEY")
    if key:
        return key
    if ENV == "dev":
        return secrets.token_hex(32)
    raise RuntimeError("SESSION_SECRET_KEY 환경변수가 필요합니다.")


SESSION_SECRET_KEY: str = _resolve_session_secret_key()

# 사업관리 화면 신규등록 버튼 활성화 (개발/정비용)
# 실 서비스 배포 시 false로 변경
ENABLE_ADMIN_CONTRACT_CREATE: bool = os.getenv("ENABLE_ADMIN_CONTRACT_CREATE", "true").lower() in ("true", "1", "yes")

# 초기 관리자 bootstrap (선택)
BOOTSTRAP_ADMIN_LOGIN_ID: str | None = os.getenv("BOOTSTRAP_ADMIN_LOGIN_ID")
BOOTSTRAP_ADMIN_PASSWORD: str | None = os.getenv("BOOTSTRAP_ADMIN_PASSWORD")
BOOTSTRAP_ADMIN_NAME: str = os.getenv("BOOTSTRAP_ADMIN_NAME", "관리자")
