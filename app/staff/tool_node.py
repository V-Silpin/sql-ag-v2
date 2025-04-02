from langgraph.types import Command
from pydantic import BaseModel, Field
from typing import List, Dict, Literal
import re

from utilities.func import State

from toolkit.tool import list_tables_tool, get_schema_tool

def remove_after_char(s, char):
    return re.sub(f'{re.escape(char)}.*', '', s)

def list_tables_node(state: State) -> Command[Literal["interpreter_agent_node"]]:
    question = state["question"]
    list_tables = list_tables_tool.invoke("")
    state_data = {
        "question": question, 
        "list_tables": list_tables, 
        "table_target": None, 
        "schema": None,
        "column_target": None,
        "generation": None,
        "data": None,
        "error": None,
        "answer": None
        }
    return Command(
        update=state_data,
        goto="interpreter_agent_node",
    )

def get_schema_node(state: State) -> Command[Literal["selector_agent_node"]]:
    tables = state["table_target"]
    schema_data = []
    
    for i in tables:
        res = get_schema_tool.invoke(i)
        result = remove_after_char(res, '/')
        schema_data.append(result)

    return Command(
        update={"schema": schema_data},
        goto="selector_agent_node",
    )