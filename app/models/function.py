import uuid
from datetime import datetime
from typing import Any, List

from sqlalchemy import String, DateTime, Boolean, Integer, UniqueConstraint, ForeignKey
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Function(Base):
    __tablename__ = "functions"
    __table_args__ = (UniqueConstraint("name", "category_id", name="uq_functions_name_category"),)

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String, nullable=False)
    returnType: Mapped[str] = mapped_column(String(50), nullable=False)
    signature: Mapped[List[Any]] = mapped_column(JSON, nullable=True)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    category_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("function_categories.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
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

    category: Mapped["FunctionCategory"] = relationship("FunctionCategory", back_populates="functions")
