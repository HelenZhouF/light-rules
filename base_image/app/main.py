import json
import os
import sys
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Ruleset Executor")

RULESET_CODE_MODULE = "ruleset_code"
RULESET_METADATA_FILE = "/app/ruleset_metadata.json"

_ruleset_execute_func = None
_ruleset_metadata: Optional[Dict[str, Any]] = None


def _load_ruleset_code():
    global _ruleset_execute_func
    
    if _ruleset_execute_func is not None:
        return _ruleset_execute_func
    
    try:
        import importlib
        import importlib.util
        
        code_path = f"/app/{RULESET_CODE_MODULE}.py"
        if not os.path.exists(code_path):
            raise RuntimeError(f"Ruleset code not found at {code_path}")
        
        spec = importlib.util.spec_from_file_location(RULESET_CODE_MODULE, code_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Failed to load ruleset code from {code_path}")
        
        module = importlib.util.module_from_spec(spec)
        sys.modules[RULESET_CODE_MODULE] = module
        spec.loader.exec_module(module)
        
        execute_funcs = [
            name for name in dir(module)
            if name.startswith("execute_") and callable(getattr(module, name))
        ]
        
        if not execute_funcs:
            raise RuntimeError("No execute function found in ruleset code")
        
        _ruleset_execute_func = getattr(module, execute_funcs[0])
        return _ruleset_execute_func
    
    except Exception as e:
        raise RuntimeError(f"Failed to load ruleset code: {e}") from e


def _load_ruleset_metadata() -> Dict[str, Any]:
    global _ruleset_metadata
    
    if _ruleset_metadata is not None:
        return _ruleset_metadata
    
    try:
        if not os.path.exists(RULESET_METADATA_FILE):
            raise RuntimeError(f"Ruleset metadata not found at {RULESET_METADATA_FILE}")
        
        with open(RULESET_METADATA_FILE, "r", encoding="utf-8") as f:
            _ruleset_metadata = json.load(f)
        
        return _ruleset_metadata
    
    except Exception as e:
        raise RuntimeError(f"Failed to load ruleset metadata: {e}") from e


class ExecuteRequest(BaseModel):
    inputs: Dict[str, Any]


class ExecuteResponse(BaseModel):
    success: bool
    output: Dict[str, Any]
    error: Optional[str] = None


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/metadata")
async def get_metadata():
    try:
        metadata = _load_ruleset_metadata()
        return metadata
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/execute", response_model=ExecuteResponse)
async def execute_ruleset(request: ExecuteRequest):
    try:
        execute_func = _load_ruleset_code()
        result = execute_func(request.inputs)
        return ExecuteResponse(
            success=True,
            output=result,
            error=None
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        return ExecuteResponse(
            success=False,
            output={},
            error=str(e)
        )
