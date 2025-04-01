from typing import Annotated, List, Dict
from typing_extensions import TypedDict

from langgraph.graph.message import AnyMessage, add_messages

class State(TypedDict):
    question: str
    list_tables: str
    table_target: List[str]
    schema: List[str]
    column_target: Dict[str, List[str]]
    generation: str | None
    data: str
    error: str | None
    answer: str
    messages: Annotated[list[AnyMessage], add_messages]
