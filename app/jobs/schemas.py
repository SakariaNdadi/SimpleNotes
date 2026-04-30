from typing import Literal

from pydantic import BaseModel


class EmbedAndIndexPayload(BaseModel):
    note_id: str
    user_id: str
    description: str


class NlpDiscoverPayload(BaseModel):
    note_id: str
    user_id: str
    text: str


class AiDetectTasksPayload(BaseModel):
    note_id: str
    user_id: str
    note_text: str


class Job(BaseModel):
    job_type: Literal["embed_and_index", "nlp_discover", "ai_detect_tasks"]
    payload: dict
    attempt: int = 1
