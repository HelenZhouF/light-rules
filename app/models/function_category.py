import uuid
from datetime import datetime
from typing import List

from sqlalchemy import String, DateTime, Boolean, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class FunctionCategory(Base):
    __tablename__ = "function_categories"
    __table_args__ = (UniqueConstraint("name", name="uq_function_categories_name"),)

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=True)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
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

    functions: Mapped[List["Function"]] = relationship("Function", back_populates="category", cascade="all, delete-orphan")
