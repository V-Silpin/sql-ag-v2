"""
SQL Agent with LangChain
"""
from typing import Optional, Dict, Any, List
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from langchain.agents.agent import AgentExecutor
from langchain.agents.agent_types import AgentType
from utils.model import get_llm
from utils.database import get_db_manager
import pandas as pd


class SQLAgent:
    """
    LangChain-powered SQL Agent for natural language to SQL queries
    """
    
    def __init__(self, model_name: str = "gemini-1.5-flash", temperature: float = 0):
        """
        Initialize SQL Agent
        
        Args:
            model_name: LLM model to use
            temperature: Temperature for LLM responses
        """
        self.llm = get_llm(model_name=model_name, temperature=temperature)
        self.db_manager = get_db_manager()
        self._agent: Optional[AgentExecutor] = None
        self._langchain_db: Optional[SQLDatabase] = None
    
    @property
    def langchain_db(self) -> SQLDatabase:
        """Get LangChain SQLDatabase instance"""
        if self._langchain_db is None:
            self._langchain_db = SQLDatabase.from_uri(self.db_manager.database_url)
        return self._langchain_db
    
    @property
    def agent(self) -> AgentExecutor:
        """Get or create SQL agent"""
        if self._agent is None:
            self._agent = create_sql_agent(
                llm=self.llm,
                db=self.langchain_db,
                agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
                verbose=True,
                handle_parsing_errors=True,
                max_iterations=10,
                max_execution_time=60
            )
        return self._agent
    
    def run_query(self, question: str) -> Dict[str, Any]:
        """
        Run a natural language query
        
        Args:
            question: Natural language question about the database
            
        Returns:
            Dictionary with query results and metadata
        """
        try:
            # Run the agent
            result = self.agent.invoke({"input": question})
            
            return {
                "success": True,
                "question": question,
                "answer": result.get("output", ""),
                "intermediate_steps": self._format_steps(result.get("intermediate_steps", []))
            }
        except Exception as e:
            return {
                "success": False,
                "question": question,
                "error": str(e),
                "answer": f"Error processing query: {str(e)}"
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


# Global SQL agent instance
_sql_agent: Optional[SQLAgent] = None


def get_sql_agent(model_name: str = "gemini-1.5-flash", temperature: float = 0) -> SQLAgent:
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
