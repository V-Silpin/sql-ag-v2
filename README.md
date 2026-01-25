# SQL Agent Backend

A LangChain-powered SQL agent that converts natural language questions into SQL queries.

## Features

- 🤖 **Natural Language to SQL**: Ask questions in plain English
- 🗄️ **PostgreSQL Database**: Full SQL database support
- 📦 **MinIO Object Storage**: S3-compatible file storage
- 🚀 **FastAPI Backend**: High-performance async API
- 🔗 **LangChain Integration**: Powered by Google Gemini
- 🐳 **Docker Support**: Fully containerized setup

## Quick Start

### 1. Setup Environment Variables

Copy the example environment file and add your API keys:

```bash
cp .env.example .env
```

Edit `.env` and add your Google API key:
```
GOOGLE_API_KEY=your_actual_api_key_here
```

### 2. Start Services with Docker

```bash
cd ..
docker-compose up -d
```

This will start:
- PostgreSQL (port 5432)
- MinIO (ports 9000, 9001)
- Backend API (port 8003)

### 3. Access Services

- **Backend API**: http://localhost:8003
- **API Docs**: http://localhost:8003/docs
- **MinIO Console**: http://localhost:9001 (login: minioadmin/minioadmin123)
- **PostgreSQL**: localhost:5432 (user: sqlagent, pass: sqlagent123)

## API Endpoints

### Query Endpoints

**POST /api/query** - Query database with natural language
```json
{
  "question": "How many users are in the database?",
  "model_name": "gemini-3-flash-preview",
  "temperature": 0
}
```

**POST /api/execute-sql** - Execute SQL directly
```json
{
  "query": "SELECT * FROM users LIMIT 10"
}
```

**GET /api/database/info** - Get database schema information

**GET /api/database/test** - Test database connection

### Storage Endpoints

**GET /api/storage/test** - Test MinIO connection

**POST /api/storage/create-bucket?bucket_name=my-bucket** - Create bucket

**GET /api/storage/list-files?bucket_name=my-bucket** - List files

## Development Setup

### Local Development (without Docker)

1. Install dependencies:
```bash
uv sync
```

2. Start PostgreSQL and MinIO locally or use Docker:
```bash
docker-compose up postgres minio
```

3. Run the backend:
```bash
python main.py
```

## Project Structure

```
backend/
├── api/
│   ├── __init__.py
│   └── routes.py          # FastAPI routes
├── staff/
│   ├── __init__.py
│   └── sql_agent.py       # LangChain SQL agent
├── toolkit/
│   └── __init__.py
├── utils/
│   ├── __init__.py
│   ├── model.py           # LLM configuration
│   ├── database.py        # Database utilities
│   └── storage.py         # MinIO utilities
├── main.py                # FastAPI application
├── pyproject.toml         # Dependencies
├── Dockerfile
└── .env.example
```

## Usage Examples

### Example 1: Natural Language Query

```python
import requests

response = requests.post("http://localhost:8003/api/query", json={
    "question": "What are the top 5 customers by total order value?"
})
print(response.json())
```

### Example 2: Database Info

```python
response = requests.get("http://localhost:8003/api/database/info")
info = response.json()
print(f"Tables: {info['tables']}")
```

### Example 3: Create Sample Data

```python
# Connect to PostgreSQL and create sample tables
response = requests.post("http://localhost:8003/api/execute-sql", json={
    "query": """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100),
            email VARCHAR(100),
            created_at TIMESTAMP DEFAULT NOW()
        )
    """
})
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_API_KEY` | Google Gemini API key | Required |
| `DATABASE_URL` | PostgreSQL connection URL | See docker-compose.yml |
| `MINIO_ENDPOINT` | MinIO endpoint | localhost:9000 |
| `MINIO_ACCESS_KEY` | MinIO access key | minioadmin |
| `MINIO_SECRET_KEY` | MinIO secret key | minioadmin123 |
| `PORT` | API server port | 8003 |

## Troubleshooting

### Database Connection Issues

```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# View PostgreSQL logs
docker-compose logs postgres
```

### MinIO Connection Issues

```bash
# Check if MinIO is running
docker-compose ps minio

# Access MinIO console
open http://localhost:9001
```

### Agent Not Responding

- Verify `GOOGLE_API_KEY` is set correctly
- Check API quotas and rate limits
- Review logs: `docker-compose logs backend`

## Tech Stack

- **Backend**: FastAPI, Python 3.11+
- **LLM**: Google Gemini via LangChain
- **Database**: PostgreSQL 16
- **Storage**: MinIO
- **ORM**: SQLAlchemy
- **Package Manager**: uv