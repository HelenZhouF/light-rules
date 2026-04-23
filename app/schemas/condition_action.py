import uuid
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ConditionType(str, Enum):
    DECISION_TABLE = "decisionTable"
    EXPRESSION = "expression"


class ActionType(str, Enum):
    ASSIGNMENT = "assignment"


class TermRef(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class ConditionBase(BaseModel):
    term: TermRef
    expression: str
    type: ConditionType = ConditionType.EXPRESSION


class ConditionCreate(ConditionBase):
    pass


class ConditionUpdate(BaseModel):
    term: Optional[TermRef] = None
    expression: Optional[str] = None
    type: Optional[ConditionType] = None


class ConditionResponse(ConditionBase):
    id: uuid.UUID
    status: Optional[str] = None
    statusMessage: Optional[str] = None

    model_config = {
        "from_attributes": True,
    }


class ActionBase(BaseModel):
    term: TermRef
    expression: str
    type: ActionType = ActionType.ASSIGNMENT


class ActionCreate(ActionBase):
    pass


class ActionUpdate(BaseModel):
    term: Optional[TermRef] = None
    expression: Optional[str] = None
    type: Optional[ActionType] = None


class ActionResponse(ActionBase):
    id: uuid.UUID
    status: Optional[str] = None
    statusMessage: Optional[str] = None

    model_config = {
        "from_attributes": True,
    }
