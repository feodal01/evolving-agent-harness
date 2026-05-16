from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ShellArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command: str = Field(min_length=1)


class ReadFileArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1)
    start_line: int = Field(default=1, ge=1)
    max_lines: int = Field(default=200, ge=1, le=400)

    @field_validator("start_line", "max_lines", mode="before")
    @classmethod
    def _coerce_uint_fields(cls, value: Any) -> Any:
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())
        return value


class WriteFileArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1)
    content: str


class FinishArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1)


class AgentAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thought: str = Field(min_length=1)
    action: Literal["run_shell", "read_file", "write_file", "finish"]
    args: ShellArgs | ReadFileArgs | WriteFileArgs | FinishArgs
