from typing import Literal
from pydantic import BaseModel

Lang = Literal["hi", "kn", "en"]
Intent = Literal[
    "CREATE_TRANSACTION", "CORRECTION", "UNDO_LAST",
    "QUERY_BALANCE", "QUERY_DAILY_TOTAL", "QUERY_DAY_SUMMARY",
    "CONFIRM", "CHOOSE_CUSTOMER", "UNKNOWN"
]

class Transcript(BaseModel):
    text: str
    language: Lang | None = None
    latency_ms: int | None = None
