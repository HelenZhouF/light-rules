from enum import Enum
from typing import List, Optional, Any

from pydantic import BaseModel, Field, model_validator


class DataType(str, Enum):
    STRING = "string"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    DATAGRID = "dataGrid"


class Direction(str, Enum):
    INPUT = "input"
    OUTPUT = "output"


class SignatureTerm(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    dataType: DataType
    direction: Optional[Direction] = None
    length: Optional[int] = Field(None, ge=1)
    defaultValue: Optional[Any] = None
    dataGridExtension: Optional[List["SignatureTerm"]] = None

    @model_validator(mode="after")
    def validate_signature_term(self) -> "SignatureTerm":
        if self.dataType == DataType.DATAGRID:
            if self.dataGridExtension is None:
                raise ValueError("dataGridExtension is required when dataType is 'dataGrid'")
            if len(self.dataGridExtension) == 0:
                raise ValueError("dataGridExtension cannot be empty when dataType is 'dataGrid'")
        elif self.dataGridExtension is not None:
            raise ValueError("dataGridExtension should only be set when dataType is 'dataGrid'")

        if self.dataType == DataType.STRING and self.length is None:
            raise ValueError("length is required when dataType is 'string'")

        if self.dataType not in [DataType.STRING, DataType.DECIMAL] and self.length is not None:
            raise ValueError("length can only be set for 'string' or 'decimal' data types")

        return self


SignatureTerm.model_rebuild()
