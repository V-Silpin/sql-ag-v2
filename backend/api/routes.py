"""
API Routes for SQL Agent
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from staff.sql_agent import get_sql_agent
from utils.database import get_db_manager
from utils.storage import get_storage_manager

router = APIRouter()


# Request/Response Models
class QueryRequest(BaseModel):
    question: str = Field(..., description="Natural language question about the database")
    model_name: Optional[str] = Field("gemini-3-flash-preview", description="LLM model to use")
    temperature: Optional[float] = Field(0, ge=0, le=2, description="Temperature for response generation")


class ReportRequest(BaseModel):
    question: str = Field(..., description="Natural language question about the database")
    model_name: Optional[str] = Field("gemini-3-flash-preview", description="LLM model to use")
    temperature: Optional[float] = Field(0, ge=0, le=2, description="Temperature for response generation")
    bucket_name: Optional[str] = Field("reports", description="MinIO bucket name for storing reports")
    expires: Optional[int] = Field(3600, ge=60, le=86400, description="Download URL expiration in seconds (1 hour - 24 hours)")


class SQLRequest(BaseModel):
    query: str = Field(..., description="SQL query to execute")


class QueryResponse(BaseModel):
    success: bool
    question: Optional[str] = None
    answer: Optional[str] = None
    error: Optional[str] = None
    intermediate_steps: Optional[list] = None


class ReportResponse(BaseModel):
    success: bool
    question: Optional[str] = None
    answer: Optional[str] = None
    download_url: Optional[str] = None
    filename: Optional[str] = None
    bucket_name: Optional[str] = None
    row_count: Optional[int] = None
    expires_in: Optional[int] = None
    sql_query: Optional[str] = None
    error: Optional[str] = None


class DatabaseInfoResponse(BaseModel):
    success: bool
    dialect: Optional[str] = None
    tables: Optional[list] = None
    table_info: Optional[str] = None
    error: Optional[str] = None


# Routes
@router.post("/api/query", response_model=QueryResponse)
async def query_database(request: QueryRequest):
    """
    Query the database using natural language
    
    Args:
        request: QueryRequest with question and optional parameters
        
    Returns:
        QueryResponse with answer and metadata
    """
    try:
        agent = get_sql_agent(
            model_name=request.model_name,
            temperature=request.temperature
        )
        result = agent.run_query(request.question)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/query/report", response_model=ReportResponse)
async def generate_report(request: ReportRequest):
    """
    Query the database and generate an Excel report with download link
    
    Args:
        request: ReportRequest with question and optional parameters
        
    Returns:
        ReportResponse with download URL and metadata
    """
    try:
        agent = get_sql_agent(
            model_name=request.model_name,
            temperature=request.temperature
        )
        result = agent.generate_excel_report(
            question=request.question,
            bucket_name=request.bucket_name,
            expires=request.expires
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/execute-sql")
async def execute_sql(request: SQLRequest):
    """
    Execute a SQL query directly
    
    Args:
        request: SQLRequest with SQL query
        
    Returns:
        Query results
    """
    try:
        agent = get_sql_agent()
        result = agent.execute_sql(request.query)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/database/info", response_model=DatabaseInfoResponse)
async def get_database_info():
    """
    Get information about the connected database
    
    Returns:
        Database information including tables and schema
    """
    try:
        agent = get_sql_agent()
        info = agent.get_database_info()
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/database/test")
async def test_database_connection():
    """
    Test database connection
    
    Returns:
        Connection status
    """
    try:
        db_manager = get_db_manager()
        is_connected = db_manager.test_connection()
        return {
            "success": is_connected,
            "message": "Database connection successful" if is_connected else "Database connection failed"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/storage/test")
async def test_storage_connection():
    """
    Test MinIO storage connection
    
    Returns:
        Connection status
    """
    try:
        storage = get_storage_manager()
        is_connected = storage.test_connection()
        return {
            "success": is_connected,
            "message": "Storage connection successful" if is_connected else "Storage connection failed"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/storage/create-bucket")
async def create_bucket(bucket_name: str):
    """
    Create a MinIO bucket
    
    Args:
        bucket_name: Name of the bucket to create
        
    Returns:
        Creation status
    """
    try:
        storage = get_storage_manager()
        success = storage.create_bucket(bucket_name)
        return {
            "success": success,
            "bucket_name": bucket_name,
            "message": f"Bucket '{bucket_name}' created successfully" if success else "Failed to create bucket"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/storage/list-files")
async def list_files(bucket_name: str, prefix: str = ""):
    """
    List files in a MinIO bucket
    
    Args:
        bucket_name: Name of the bucket
        prefix: Optional prefix to filter files
        
    Returns:
        List of files
    """
    try:
        storage = get_storage_manager()
        files = storage.list_files(bucket_name, prefix)
        return {
            "success": True,
            "bucket_name": bucket_name,
            "files": files,
            "count": len(files)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
