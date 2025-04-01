from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_groq import ChatGroq
from langchain_community.utilities import SQLDatabase
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import Tool
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import os
from dotenv import load_dotenv

load_dotenv()
google_api_key = os.getenv("GEMINI_API_KEY")
connection_string = os.getenv("CONNECTION_STRING")

llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=google_api_key) #ChatGroq(groq_api_key=groq_api_key, model_name="Llama3-8b-8192")

db = SQLDatabase.from_uri(connection_string)

toolkit = SQLDatabaseToolkit(db=db, llm=llm)
tools = toolkit.get_tools()

list_tables_tool = next(tool for tool in tools if tool.name == "sql_db_list_tables")
get_schema_tool = next(tool for tool in tools if tool.name == "sql_db_schema")

#@tool
def db_query_tool(query: str) -> str:
    """
    Execute a SQL query against the database and get back the result.
    If the query is not correct, an error message will be returned.
    If an error is returned, rewrite the query, check the query, and try again.
    """
    result = db.run_no_throw(query)
    if not result:
        return "Error: Query failed. Please rewrite your query and try again."
    return result

query_tool = Tool(
        name="db_query_tool",
        description="Executes SQL query",
        func=db_query_tool,
    )