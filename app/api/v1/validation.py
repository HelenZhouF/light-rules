import json
import re
from typing import List

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from app.schemas.validation import (
    FunctionValidationRequest,
    FunctionValidationResponse,
    ValidationError,
    VALIDATION_ERROR_CODE,
    VALIDATION_WARNING_CODE,
)


VALIDATION_FUNCTION_MEDIA_TYPE = "application/vnd.sas.business.rule.function+json"


router = APIRouter(
    prefix="/commons/validations/functions",
    tags=["validations"],
)


def _error(message: str) -> ValidationError:
    return ValidationError(errorCode=VALIDATION_ERROR_CODE, errorMessage=message)


def _warning(message: str) -> ValidationError:
    return ValidationError(errorCode=VALIDATION_WARNING_CODE, errorMessage=message)


def _validate_ds2_code(code: str) -> List[ValidationError]:
    errors: List[ValidationError] = []

    if ";" not in code:
        errors.append(_error("The method declaration must end with a semicolon"))
        return errors

    declaration_part = code[:code.index(";")].strip()

    method_match = re.match(
        r"^\s*method\s+(?:(\w+)\s+)?(\w+)\s*\((.*)\)\s*$",
        declaration_part,
        re.IGNORECASE,
    )
    if not method_match:
        errors.append(_error("The method declaration is not valid"))
        return errors

    return_type = method_match.group(1)
    method_name = method_match.group(2)
    params_str = method_match.group(3) or ""

    allowed_types = {
        "integer", "int", "double", "float", "char", "varchar",
        "string", "binary", "decimal", "numeric", "bigint",
        "smallint", "tinyint", "date", "time", "datetime",
    }
    if params_str.strip():
        for idx, raw_param in enumerate(params_str.split(","), start=1):
            param = raw_param.strip()
            if not param:
                errors.append(_warning(f"Parameter {idx} is empty"))
                continue

            param_lower = param.lower()
            for prefix in ("in_out ", "inout ", "out ", "in "):
                if param_lower.startswith(prefix):
                    param = param[len(prefix):].strip()
                    break

            parts = param.split()
            if len(parts) < 2:
                errors.append(_error(f"Parameter '{raw_param.strip()}' must have a type and a name"))
                continue

            ptype = parts[0]
            if ptype.lower() not in allowed_types:
                errors.append(_warning(f"Unknown parameter type '{ptype}' for parameter {idx}"))

    body = code[code.index(";") + 1:]
    if not re.search(r"\bend\b\s*;?\s*$", body.strip(), re.IGNORECASE):
        errors.append(_error("The method body must be closed with 'end;'"))

    body_without_end = re.sub(r"\bend\b\s*;?\s*$", "", body, flags=re.IGNORECASE).strip()
    if body_without_end and body_without_end.strip(";").strip() == "":
        errors.append(_warning("The method body appears empty or does not contain statements"))

    if return_type is None and "return" not in body.lower():
        errors.append(_warning("Method does not declare a return type"))

    return errors


@router.post(
    "",
    response_model=FunctionValidationResponse,
    status_code=status.HTTP_200_OK,
)
async def validate_custom_function(request: Request):
    content_type = request.headers.get("content-type", "")
    if VALIDATION_FUNCTION_MEDIA_TYPE not in content_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported Media Type. Expected '{VALIDATION_FUNCTION_MEDIA_TYPE}'",
        )

    try:
        raw_body = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON body",
        )

    try:
        payload = FunctionValidationRequest.model_validate(raw_body)
    except PydanticValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=json.loads(exc.json()),
        )

    try:
        validation_errors = _validate_ds2_code(payload.code)
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to validate function code: {exc}",
        )

    response = FunctionValidationResponse(errors=validation_errors)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=response.model_dump(by_alias=True, exclude_none=True),
        media_type=VALIDATION_FUNCTION_MEDIA_TYPE,
    )
