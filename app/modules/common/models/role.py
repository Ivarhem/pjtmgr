from sqlalchemy import Boolean, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import TimestampMixin
from app.core.database import Base


class Role(TimestampMixin, Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    permissions: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # permissions structure:
    # {
    #   "admin": bool,
    #   "modules": {"accounting": "full"|"read"|null, "infra": "full"|"read"|null}
    #   // Future full RBAC extension:
    #   // "resources": {"contract": ["create","read","update","delete"], ...}
    # }
