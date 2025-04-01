from langgraph.graph import END, StateGraph, START

from staff.agent_node import interpreter_agent_node, selector_agent_node, scribe_agent_node, verify_agent_node, executor_agent_node, summary_agent_node
from staff.tool_node import list_tables_node, get_schema_node

from utilities.func import State

workflow = StateGraph(State)

workflow.add_node("list_tables_node", list_tables_node)
workflow.add_node("interpreter_agent_node", interpreter_agent_node)
workflow.add_node("get_schema_node", get_schema_node)
workflow.add_node("selector_agent_node", selector_agent_node)
workflow.add_node("scribe_agent_node", scribe_agent_node)
workflow.add_node("verify_agent_node", verify_agent_node)
workflow.add_node("executor_agent_node", executor_agent_node)
workflow.add_node("summary_agent_node", summary_agent_node)

workflow.add_edge(START, "list_tables_node")

graph = workflow.compile()