from datetime import datetime
from pydantic import BaseModel


class RoadmapRequest(BaseModel):
    goal: str


class RoadmapStep(BaseModel):
    order: int
    title: str
    description: str
    skills: list[str]
    duration: str


class RoadmapJson(BaseModel):
    goal: str
    steps: list[RoadmapStep]


class RoadmapResponse(BaseModel):
    id: int
    user_input: str
    initial_json: dict | None
    critique: str | None
    final_text: str | None
    final_json: dict | None
    model_name: str | None
    input_tokens: int | None
    output_tokens: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RoadmapSummary(BaseModel):
    id: int
    user_input: str
    created_at: datetime

    model_config = {"from_attributes": True}
