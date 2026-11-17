from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)


class Source(BaseModel):
    id: str
    title: str
    source: str


class ResearchResponse(BaseModel):
    run_id: str
    answer: str
    verified: bool
    sources: list[Source]


class Verdict(BaseModel):
    grounded: bool
    reason: str
