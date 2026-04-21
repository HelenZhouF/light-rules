import uuid
from datetime import datetime
from typing import Any, List

from sqlalchemy import String, DateTime, Boolean, Integer, UniqueConstraint
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class RuleSet(Base):
    __tablename__ = "rulesets"
    __table_args__ = (UniqueConstraint("name", name="uq_rulesets_name"),)

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    ruleSetType: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=True)
    signature: Mapped[List[Any]] = mapped_column(JSON, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by: Mapped[str] = mapped_column(String(255), nullable=True)
    created_datetime: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )
    modified_by: Mapped[str] = mapped_column(String(255), nullable=True)
    modified_datetime: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    rules: Mapped[List["Rule"]] = relationship("Rule", back_populates="ruleset", cascade="all, delete-orphan")
