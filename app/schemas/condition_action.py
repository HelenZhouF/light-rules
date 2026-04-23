import uuid
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.schemas.signature import SignatureTerm


class ConditionType(str, Enum):
    DECISION_TABLE = "decisionTable"
    EXPRESSION = "expression"


class ActionType(str, Enum):
    ASSIGNMENT = "assignment"


class TermRef(BaseModel):
    termId: Optional[uuid.UUID] = None
    name: Optional[str] = Field(None, min_length=1, max_length=255)

    @model_validator(mode="after")
    def validate_term_ref(self) -> "TermRef":
        if self.termId is None and self.name is None:
            raise ValueError("Either termId or name must be provided")
        return self


class TermRefResponse(BaseModel):
    id: Optional[uuid.UUID] = None
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    dataType: Optional[DataType] = None
    direction: Optional[Direction] = None
    length: Optional[int] = Field(None, ge=1)
    defaultValue: Optional[Any] = None
    dataGridExtension: Optional[List["TermRefResponse"]] = None


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


class ConditionResponseBase(BaseModel):
    term: TermRefResponse
    expression: str
    type: ConditionType = ConditionType.EXPRESSION


class ConditionResponse(ConditionResponseBase):
    id: uuid.UUID
    status: Optional[str] = None
    statusMessage: Optional[str] = None


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


class ActionResponseBase(BaseModel):
    term: TermRefResponse
    expression: str
    type: ActionType = ActionType.ASSIGNMENT


class ActionResponse(ActionResponseBase):
    id: uuid.UUID
    status: Optional[str] = None
    statusMessage: Optional[str] = None


TermRefResponse.model_rebuild()
