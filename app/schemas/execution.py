from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ConditionExecutionResult(BaseModel):
    id: str
    termName: str
    expression: str
    result: bool
    error: Optional[str] = None


class ActionExecutionResult(BaseModel):
    id: str
    termName: str
    expression: str
    value: Any
    error: Optional[str] = None


class RuleExecutionResult(BaseModel):
    id: str
    name: str
    orderIndex: int
    conditional: str
    conditionsPassed: bool
    conditions: List[ConditionExecutionResult]
    actions: List[ActionExecutionResult]
    error: Optional[str] = None


class ExecutionResponse(BaseModel):
    success: bool
    output: Dict[str, Any]
    rules: List[RuleExecutionResult]
    error: Optional[str] = None

    model_config = {
        "by_alias": True,
        "exclude_none": True,
    }


class ExecutionRequest(BaseModel):
    input: Dict[str, Any] = Field(..., description="Input data matching the ruleset signature")
