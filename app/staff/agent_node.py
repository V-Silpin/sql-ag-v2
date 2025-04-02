import json

from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import JsonOutputParser
from langgraph.types import Command
from langgraph.graph import END

from pydantic import BaseModel, Field
from typing import List, Dict, Literal

from utilities.func import State

from toolkit.tool import db_query_tool

import os
from dotenv import load_dotenv

load_dotenv()
google_api_key = os.getenv("GEMINI_API_KEY")

examples = None

with open("app/staff/few_shot/examples.json", "r", encoding='utf-8', errors='ignore') as f:
    examples = json.load(f)

llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=google_api_key)

interpreter = '''
You are an input prompt analyzer designed to identify user requirements and correlate them with relevant SQL database tables.

Your task is to analyze the user's question and determine the associated table names and column names based on the context provided. 

For example, if a user asks, "What is the MSRP for a product?", you should identify the relevant tables and columns related to "product" and "MSRP".

ONLY GENERATE THE SQL QUERY, DON'T USE MARKDOWN SYNTAX TO GENERATE RESULTS

Your output should follow this format:

{{"table_target" : ["table1", "table2", "table3", ...]}}

- Ensure that "table_target" remains in the output, and populate the list with the names of the relevant tables.
- If you cannot identify any relevant tables, simply return "NULL".

Question: {input}
'''

interpreter_prompt = ChatPromptTemplate.from_template(
    interpreter
)

interpreter_agent = interpreter_prompt | llm

def interpreter_agent_node(state: State) -> Command[Literal["get_schema_node"]]:
    question = state["question"]
    list_tables = state["list_tables"]
    query = question + "\nList of tables: " + list_tables
    response = interpreter_agent.invoke({"input": query})
    txt = response.text()
    txt.replace("`", "")
    txt.replace("json", "")
    json_data = json.loads(txt)
    return Command(
        update=json_data,
        goto="get_schema_node",
    )

selector = """
Todo task Reference:

{todo}

Your task is to identify and retrieve the column names from the specified input table targets.
Use the tool that can provide the schema of each table.
Also if there are two or more tables present in the table targets, then include those columns which are FOREIGN KEY
to other tables

ONLY GENERATE THE SQL QUERY, DON'T USE MARKDOWN SYNTAX TO GENERATE RESULTS

Below are the tables from which you need to extract the columns:
{input}

Also here is the schema of each table:
{schema}

Your output should follow this format only:

{{
    "column_target" : {{
        "table_name_1" : [column_name_1, column_name_2, column_name_3, ...],
        "table_name_2" : [column_name_1, column_name_2, column_name_3, ...],
        "table_name_3" : [column_name_1, column_name_2, column_name_3, ...],
        "table_name_4" : [column_name_1, column_name_2, column_name_3, ...]
    }}
}}

- Ensure that "column_target" remains in the output, and populate the list with the names of the relevant columns for each table.
- If you cannot identify any relevant columns, simply return "NULL".

"""

selector_prompt = ChatPromptTemplate.from_template(
    selector
)

class Column(BaseModel):
    column_target: Dict[str, List[str]] = Field(description="One part is table name & it has a list of columns")


selector_json_parser = JsonOutputParser(pydantic_object=Column)

selector_agent = selector_prompt | llm | selector_json_parser

def selector_agent_node(state: State) -> Command[Literal["scribe_agent_node", "interpreter_agent_node"]]:
    question = state["question"]
    table_target = state["table_target"]
    table_target_str = "\nTable that you have to find the columns: \n[" + ", ".join(table_target) + "]"
    schema_data = state["schema"]
    schema = ""
    for i in schema_data:
        schema += (i+"\n")
    
    response = selector_agent.invoke({"todo": question, "input": table_target_str, "schema": schema})
   # if response == "NULL":
    #    return Command(
    #    update=response,
    #    goto="interpreter_agent_node",
    #)
    return Command(
        update=response,
        goto="scribe_agent_node",
    )

scribe = """You are a SQL expert with a strong attention to detail.

Given an input question, output a syntactically correct SQLite query to run, then look at the results of the query and return the answer.

DO NOT call any tool besides SubmitFinalAnswer to submit the final answer.

When generating the query:

Output the SQL query that answers the input question without a tool call.

Unless the user specifies a specific number of examples they wish to obtain, always limit your query to at most 5 results.
You can order the results by a relevant column to return the most interesting examples in the database.
Never query for all the columns from a specific table, only ask for the relevant columns given the question.

If you get an error while executing a query, rewrite the query and try again.

If you get an empty result set, you should try to rewrite the query to get a non-empty result set. 
NEVER make stuff up if you don't have enough information to answer the query... just say you don't have enough information.

If you have enough information to answer the input question, simply invoke the appropriate tool to submit the final answer to the user.

DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database.

Given question, table & column target from which you have to create your sql query:

Also a error log & the sql query will be given if the sql query didn't work out.
So modify the query to avoid errors & get the right result.

ONLY GENERATE THE SQL QUERY, FOR GOD'S SAKE DON'T USE MARKDOWN SYNTAX TO GENERATE RESULTS

Examples:
{examples}

Question:
{input}

Tables:
{table_target}

Columns:
{column_target}

Earlier Generated Query:
{query}

Error Log:
{errorlog}
"""

scribe_prompt = ChatPromptTemplate.from_template(
    scribe
)

scribe_agent = scribe_prompt | llm

def scribe_agent_node(state: State) -> Command[Literal["verify_agent_node"]]:
    question = state["question"]
    table_target = state["table_target"]
    column_target = state["column_target"]
    query = state["generation"]
    error = state["error"]

    if query == None:
        query = "SQL Query not required"

    if error == None:
        error = "No Error"

    response = scribe_agent.invoke({"examples": examples, "input" : question, "table_target" : table_target, "column_target": column_target, "query": query,"errorlog": error})
    text = response.text()
    text = text.replace("sqlite", "")
    text = text.replace("`", "")
    text = text.replace(";", "")
    text = text.replace("\n", "")
    return Command(
        update={
            "generation": text
        },
        goto="verify_agent_node",
    )

verify = """You are a SQL expert with a strong attention to detail.
You will be provided a sql query that will be run on mysql
Double check the SQLite query for common mistakes, including:
- Using NOT IN with NULL values
- Using UNION when UNION ALL should have been used
- Using BETWEEN for exclusive ranges
- Data type mismatch in predicates
- Properly quoting identifiers
- Using the correct number of arguments for functions
- Casting to the correct data type
- Using the proper columns for joins

If there are any of the above mistakes, return only NULL.
Else return True.

ONLY GENERATE THE SQL QUERY, FOR GOD'S SAKE DON'T USE MARKDOWN SYNTAX TO GENERATE RESULTS

Query:
{input}
"""

verify_prompt = ChatPromptTemplate.from_template(
    verify
)
verify_agent = verify_prompt | llm

def verify_agent_node(state: State) -> Command[Literal["executor_agent_node", "scribe_agent_node"]]:
    gen = state["generation"]
    response = verify_agent.invoke({"input": gen})
    valid = response.text()
    goto = "executor_agent_node"
    if valid == "NULL":
        goto = "scribe_agent_node"
    return Command(
        update={
            "valid": valid
        },
        goto=goto,
    )

executor = """
Your task is to execute to SQL query with a sql tool

ONLY GENERATE THE SQL QUERY, FOR GOD'S SAKE DON'T USE MARKDOWN SYNTAX TO GENERATE RESULTS

Query:

{query_generation}
"""

executor_prompt = ChatPromptTemplate.from_template(
    executor
)
executor_agent = executor_prompt | llm

def executor_agent_node(state: State) -> Command[Literal["summary_agent_node", "scribe_agent_node"]]:
    gen = state["generation"]
    data = {}
    goto = "summary_agent_node"
    response = db_query_tool(gen)
    data = { "data": response }

    if "Error" in response:
        data = { "error": response }
        goto = "scribe_agent_node"
    
    return Command(
        update=data,
        goto=goto,
    )

summary = """
Your task is to summarize the data in such a way that you are answering a question
Question:
{question}

Data:
{data}
"""

summary_prompt = ChatPromptTemplate.from_template(
    summary
)
summary_agent = summary_prompt | llm

def summary_agent_node(state: State) -> Command[Literal["__end__"]]:
    question = state["question"]
    data = state["data"]

    response = summary_agent.invoke({"question": question, "data": data})

    ans = response.text()
    return Command(
        update={ "answer": ans },
        goto="__end__",
    )