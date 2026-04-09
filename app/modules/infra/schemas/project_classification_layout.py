from __future__ import annotations

from pydantic import BaseModel, Field


class ProjectClassificationLayoutUpdate(BaseModel):
    layout_id: int = Field(gt=0)


class ProjectClassificationLayoutRead(BaseModel):
    project_id: int
    layout_id: int
    layout_name: str
