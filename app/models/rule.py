import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Integer, ForeignKey, UniqueConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Rule(Base):
    __tablename__ = "rules"
    __table_args__ = (
        UniqueConstraint("rule_set_id", "name", name="uq_rules_ruleset_name"),
        UniqueConstraint("rule_set_id", "order_index", name="uq_rules_ruleset_order_index"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )
    rule_set_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rulesets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=True)
    conditional: Mapped[str] = mapped_column(Text, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
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

    ruleset: Mapped["RuleSet"] = relationship("RuleSet", back_populates="rules")
