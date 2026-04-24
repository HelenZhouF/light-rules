import uuid
from datetime import datetime
from typing import List

from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Lookup(Base):
    __tablename__ = "lookups"
    __table_args__ = (UniqueConstraint("name", name="uq_lookups_name"),)

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
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

    entries: Mapped[List["LookupEntry"]] = relationship(
        "LookupEntry",
        back_populates="lookup",
        cascade="all, delete-orphan",
        order_by="LookupEntry.key",
    )


class LookupEntry(Base):
    __tablename__ = "lookup_entries"
    __table_args__ = (
        UniqueConstraint("lookup_id", "key", name="uq_lookup_entries_lookup_id_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )
    lookup_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lookups.id", ondelete="CASCADE"),
        nullable=False,
    )
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[str] = mapped_column(String(1000), nullable=False)
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

    lookup: Mapped["Lookup"] = relationship("Lookup", back_populates="entries")
