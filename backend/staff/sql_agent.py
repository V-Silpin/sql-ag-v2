"""
SQL Agent with LangGraph
"""
from typing import Optional, Dict, Any, List, Annotated, Sequence
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict
from utils.model import get_llm
from utils.database import get_db_manager
from utils.storage import get_storage_manager
from io import BytesIO
from datetime import datetime
import pandas as pd
import uuid


class AgentState(TypedDict):
    """State for the SQL agent graph"""
    messages: Annotated[Sequence[BaseMessage], add_messages]


class SQLAgent:
    """
    LangGraph-powered SQL Agent for natural language to SQL queries
    """
    
    def __init__(self, model_name: str = "gemini-3-flash-preview", temperature: float = 0):
        """
        Initialize SQL Agent
        
        Args:
            model_name: LLM model to use
            temperature: Temperature for LLM responses
        """
        self.llm = get_llm(model_name=model_name, temperature=temperature)
        self.db_manager = get_db_manager()
        self._agent = None
        self._langchain_db: Optional[SQLDatabase] = None
        self._toolkit: Optional[SQLDatabaseToolkit] = None
    
    @property
    def langchain_db(self) -> SQLDatabase:
        """Get LangChain SQLDatabase instance"""
        if self._langchain_db is None:
            self._langchain_db = SQLDatabase.from_uri(self.db_manager.database_url)
        return self._langchain_db
    
    @property
    def toolkit(self) -> SQLDatabaseToolkit:
        """Get SQL Database toolkit with tools"""
        if self._toolkit is None:
            self._toolkit = SQLDatabaseToolkit(
                db=self.langchain_db,
                llm=self.llm
            )
        return self._toolkit
    
    @property
    def agent(self):
        """Get or create LangGraph SQL agent"""
        if self._agent is None:
            # System prompt with database context
            system_message = """You are an expert SQL agent working with a PostgreSQL database containing employee data.

DATABASE SCHEMA OVERVIEW:
The database contains employee records with the following tables:

1. **employees** - Core employee information (300,024 records)
   - emp_no (PK): Employee number
   - birth_date: Date of birth
   - first_name: First name
   - last_name: Last name
   - gender: Gender (custom type)
   - hire_date: Date of hire

2. **departments** - Department information (9 departments)
   - dept_no (PK): Department number (e.g., 'd001')
   - dept_name: Department name (unique)

3. **dept_emp** - Employee-Department assignments (shows which employees work in which departments)
   - emp_no, dept_no (Composite PK)
   - from_date: Start date of assignment
   - to_date: End date of assignment

4. **dept_manager** - Department managers
   - emp_no, dept_no (Composite PK)
   - from_date: Start date as manager
   - to_date: End date as manager

5. **salaries** - Employee salary history (2.8M+ records)
   - emp_no, from_date (Composite PK)
   - salary: Salary amount
   - to_date: End date of salary period

6. **titles** - Employee job titles (443K+ records)
   - emp_no, title, from_date (Composite PK)
   - to_date: End date of title

RELATIONSHIPS:
- All tables connect to employees via emp_no (foreign key)
- dept_emp and dept_manager link employees to departments
- Employees can have multiple salary records and titles over time

QUERY GUIDELINES:
- Use JOINs to combine employee data with departments, salaries, and titles
- Consider date ranges (from_date, to_date) for historical queries
- Use aggregations (COUNT, AVG, SUM) for analytical queries
- Filter by to_date to find current assignments/salaries (e.g., to_date = '9999-01-01' indicates current)

When answering questions:
1. First understand what data is needed
2. Write a SQL query to fetch the data
3. Execute the query using the available tools
4. Analyze the results and provide a clear answer

Generate accurate SQL queries based on the user's natural language questions."""

            # Get tools from toolkit
            tools = self.toolkit.get_tools()
            
            # Bind tools to the LLM
            llm_with_tools = self.llm.bind_tools(tools)
            
            # Create prompt template
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_message),
                MessagesPlaceholder(variable_name="messages"),
            ])
            
            # Define the agent node
            def call_model(state: AgentState):
                """Call the LLM with tools"""
                messages = prompt.invoke({"messages": state["messages"]})
                response = llm_with_tools.invoke(messages)
                return {"messages": [response]}
            
            # Define conditional edge function
            def should_continue(state: AgentState):
                """Determine whether to continue or end"""
                messages = state["messages"]
                last_message = messages[-1]
                
                # If there are no tool calls, we're done
                if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
                    return END
                return "tools"
            
            # Create the graph
            workflow = StateGraph(AgentState)
            
            # Add nodes
            workflow.add_node("agent", call_model)
            workflow.add_node("tools", ToolNode(tools))
            
            # Add edges
            workflow.add_edge(START, "agent")
            workflow.add_conditional_edges("agent", should_continue, ["tools", END])
            workflow.add_edge("tools", "agent")
            
            # Compile the graph
            self._agent = workflow.compile()
        
        return self._agent
    
    def run_query(self, question: str) -> Dict[str, Any]:
        """
        Run a natural language query using LangGraph agent
        
        Args:
            question: Natural language question about the database
            
        Returns:
            Dictionary with query results and metadata
        """
        try:
            # Run the LangGraph agent
            result = self.agent.invoke(
                {"messages": [HumanMessage(content=question)]}
            )
            
            # Extract messages from result
            messages = result.get("messages", [])
            
            # Get the final AI response
            final_answer = ""
            intermediate_steps = []
            
            for msg in messages:
                if isinstance(msg, AIMessage):
                    # Handle content that might be a string or a list of content blocks
                    if msg.content:
                        if isinstance(msg.content, str):
                            final_answer = msg.content
                        elif isinstance(msg.content, list):
                            # Extract text from content blocks
                            text_parts = []
                            for content_block in msg.content:
                                if isinstance(content_block, dict) and content_block.get("type") == "text":
                                    text_parts.append(content_block.get("text", ""))
                                elif isinstance(content_block, str):
                                    text_parts.append(content_block)
                            final_answer = " ".join(text_parts)
                        else:
                            final_answer = str(msg.content)
                    
                    # Capture tool calls
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        for tool_call in msg.tool_calls:
                            intermediate_steps.append({
                                "action": tool_call.get("name", "unknown"),
                                "action_input": str(tool_call.get("args", {}))[:500],
                                "observation": ""
                            })
            
            return {
                "success": True,
                "question": question,
                "answer": final_answer,
                "intermediate_steps": intermediate_steps,
                "messages": [self._format_message(msg) for msg in messages]
            }
        except Exception as e:
            return {
                "success": False,
                "question": question,
                "error": str(e),
                "answer": f"Error processing query: {str(e)}"
            }
    
    def _format_message(self, msg: BaseMessage) -> Dict[str, Any]:
        """Format a message for output"""
        content = msg.content
        
        # Handle content that might be a list of content blocks
        if isinstance(content, list):
            text_parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    text_parts.append(block)
            content = " ".join(text_parts)
        
        return {
            "type": msg.__class__.__name__,
            "content": content,
        }
    def _format_steps(self, steps: List) -> List[Dict[str, Any]]:
        """Format intermediate steps for better readability"""
        formatted_steps = []
        for step in steps:
            if len(step) >= 2:
                action, observation = step[0], step[1]
                formatted_steps.append({
                    "action": str(action.tool) if hasattr(action, 'tool') else str(action),
                    "action_input": str(action.tool_input) if hasattr(action, 'tool_input') else "",
                    "observation": str(observation)[:500]  # Limit observation length
                })
        return formatted_steps
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get information about the connected database"""
        try:
            table_info = self.langchain_db.get_table_info()
            return {
                "success": True,
                "dialect": self.langchain_db.dialect,
                "tables": self.langchain_db.get_usable_table_names(),
                "table_info": table_info
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def execute_sql(self, sql_query: str) -> Dict[str, Any]:
        """
        Execute a SQL query directly
        
        Args:
            sql_query: SQL query to execute
            
        Returns:
            Dictionary with query results
        """
        try:
            result = self.langchain_db.run(sql_query)
            return {
                "success": True,
                "query": sql_query,
                "result": result
            }
        except Exception as e:
            return {
                "success": False,
                "query": sql_query,
                "error": str(e)
            }
    
    def query_to_dataframe(self, sql_query: str) -> Optional[pd.DataFrame]:
        """
        Execute SQL query and return results as pandas DataFrame
        
        Args:
            sql_query: SQL query to execute
            
        Returns:
            DataFrame with query results or None on error
        """
        try:
            with self.db_manager.engine.connect() as conn:
                df = pd.read_sql_query(sql_query, conn)
            return df
        except Exception as e:
            print(f"Error executing query: {e}")
            return None
    
    def generate_excel_report(
        self, 
        question: str, 
        bucket_name: str = "reports",
        expires: int = 3600
    ) -> Dict[str, Any]:
        """
        Generate an Excel report from a natural language query and upload to MinIO
        
        Args:
            question: Natural language question about the database
            bucket_name: MinIO bucket to store the report
            expires: Presigned URL expiration time in seconds (default: 1 hour)
            
        Returns:
            Dictionary with download URL and metadata
        """
        try:
            # Run the query first to get results
            result = self.run_query(question)
            
            if not result.get("success"):
                return {
                    "success": False,
                    "error": result.get("error", "Query failed")
                }
            
            # Extract SQL query from intermediate steps
            sql_query = None
            for step in result.get("intermediate_steps", []):
                if step.get("action") in ["sql_db_query", "QuerySQLDataBaseTool"]:
                    # Extract query from action_input
                    action_input = step.get("action_input", "")
                    if "query" in action_input.lower():
                        # Parse the query from the input string
                        import re
                        match = re.search(r"SELECT.*?(?=\}|$)", action_input, re.IGNORECASE | re.DOTALL)
                        if match:
                            sql_query = match.group(0).strip()
            
            # If no SQL found in steps, try to generate from question
            if not sql_query:
                return {
                    "success": False,
                    "error": "Could not extract SQL query from agent execution"
                }
            
            # Execute query and get DataFrame
            df = self.query_to_dataframe(sql_query)
            
            if df is None or df.empty:
                return {
                    "success": False,
                    "error": "Query returned no data"
                }
            
            # Generate Excel file in memory
            excel_buffer = BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                # Write query results
                df.to_excel(writer, sheet_name='Query Results', index=False)
                
                # Add metadata sheet
                metadata_df = pd.DataFrame({
                    'Property': ['Question', 'SQL Query', 'Generated At', 'Row Count'],
                    'Value': [
                        question,
                        sql_query,
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        len(df)
                    ]
                })
                metadata_df.to_excel(writer, sheet_name='Metadata', index=False)
            
            excel_buffer.seek(0)
            excel_data = excel_buffer.getvalue()
            
            # Upload to MinIO
            storage = get_storage_manager()
            
            # Ensure bucket exists
            storage.create_bucket(bucket_name)
            
            # Generate unique filename
            filename = f"report_{uuid.uuid4().hex[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            
            # Upload file
            success = storage.upload_file(
                bucket_name=bucket_name,
                object_name=filename,
                data=excel_data,
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
            if not success:
                return {
                    "success": False,
                    "error": "Failed to upload report to storage"
                }
            
            # Generate presigned URL
            download_url = storage.get_presigned_url(
                bucket_name=bucket_name,
                object_name=filename,
                expires=expires
            )
            
            if not download_url:
                return {
                    "success": False,
                    "error": "Failed to generate download URL"
                }
            
            return {
                "success": True,
                "question": question,
                "answer": result.get("answer", ""),
                "download_url": download_url,
                "filename": filename,
                "bucket_name": bucket_name,
                "row_count": len(df),
                "expires_in": expires,
                "sql_query": sql_query
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Error generating report: {str(e)}"
            }


# Global SQL agent instance
_sql_agent: Optional[SQLAgent] = None


def get_sql_agent(model_name: str = "gemini-3-flash-preview", temperature: float = 0) -> SQLAgent:
    """
    Get global SQL agent instance
    
    Args:
        model_name: LLM model to use
        temperature: Temperature for LLM responses
        
    Returns:
        SQLAgent instance
    """
    global _sql_agent
    if _sql_agent is None:
        _sql_agent = SQLAgent(model_name=model_name, temperature=temperature)
    return _sql_agent
