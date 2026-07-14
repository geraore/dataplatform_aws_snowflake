from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class CloudEvent(BaseModel):
    model_config = ConfigDict(extra="allow")

    specversion: str
    id: str
    source: str
    type: str

    @field_validator("specversion")
    @classmethod
    def specversion_must_be_1(cls, v: str) -> str:
        if v != "1.0":
            raise ValueError(f"unsupported specversion: {v!r} — expected '1.0'")
        return v

    @field_validator("id", "source", "type")
    @classmethod
    def must_be_non_empty(cls, v: Any, info) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError(f"'{info.field_name}' must be a non-empty string")
        return v
