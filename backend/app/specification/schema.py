"""The shape of an API specification, written as Pydantic models (structural validation)."""
from typing import Literal

from pydantic import BaseModel

FieldType = Literal["string", "text", "integer", "float", "boolean", "date", "datetime", "email"]


class FieldSpec(BaseModel):
    name: str
    type: FieldType
    required: bool = True
    unique: bool = False
    type_source: str | None = None


class QueryParam(BaseModel):
    name: str
    kind: str
    type: str = "string"
    field: str | None = None
    allowed: list[str] | None = None


class EndpointSpec(BaseModel):
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    path: str
    operation: str
    summary: str = ""
    query_params: list[QueryParam] = []
    search_fields: list[str] = []


class ApiSpec(BaseModel):
    project_name: str
    slug: str
    resource: str
    resource_plural: str
    model_name: str
    table_name: str
    fields: list[FieldSpec]
    operations: list[str]
    endpoints: list[EndpointSpec]
    auth_required: bool = False
    assumptions: list[str] = []
    warnings: list[str] = []