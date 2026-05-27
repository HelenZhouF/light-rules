from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator


VALIDATION_ERROR_CODE = 13740
VALIDATION_WARNING_CODE = 13741


class ValidationError(BaseModel):
    errorCode: int = Field(...)
    errorMessage: str = Field(...)


class ValidationResponse(BaseModel):
    errors: List[ValidationError] = Field(default_factory=list)


class FunctionValidationRequest(BaseModel):
    code: str = Field(..., min_length=1)
    description: Optional[str] = None
    signature: Optional[List[Any]] = None
    testCustomContextUri: Optional[str] = None

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("code must not be blank")
        if not stripped.lower().startswith("method "):
            raise ValueError("code must start with 'method'")
        return v


class FunctionValidationResponse(BaseModel):
    errors: List[ValidationError] = Field(default_factory=list)
