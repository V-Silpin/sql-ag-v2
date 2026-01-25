"""
LLM Model Configuration
"""
import os
from langchain_google_genai import ChatGoogleGenerativeAI


def get_llm(model_name: str = "gemini-3-flash-preview", temperature: float = 0):
    """
    Get configured LLM instance
    
    Args:
        model_name: Google Gemini model name
        temperature: Temperature for response generation
        
    Returns:
        ChatGoogleGenerativeAI instance
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set")
    
    return ChatGoogleGenerativeAI(
        model=model_name,
        temperature=temperature,
        google_api_key=api_key
    )
