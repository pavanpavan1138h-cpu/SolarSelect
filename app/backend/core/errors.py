"""Stable public errors with safe messages; never serialize exception payloads."""
from typing import Any
from pydantic import BaseModel, ConfigDict

class ErrorBody(BaseModel):
    code: str
    message: str
    details: Any = None

class ErrorEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    error: ErrorBody
    request_id: str

class APIError(Exception):
    def __init__(self, status: int, code: str, message: str, details=None):
        self.status, self.code, self.message, self.details = status, code, message, details
