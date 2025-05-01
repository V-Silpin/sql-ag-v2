# SQL-Agent



## An agent built to convert natural language queries to SQL queries
---

## Workflow

### Step-by-Step Process

1. **Input**:
   - User enter his query into th website
    - The query is sent to the SQL agent

2. **List table from DB tool**:
    - First step is to retrieve list of tables from the SQL database
    - Then the user query and the list of tables is sent to the Interpreter Agent

3. **Interpreter Agent**:
    - The task of the interpreter agent is to find the target table wrt the user query & the list of tables

4. **Get Schema of a table Tool**:

    - This tool provides the schema of the table
    - It is used to find the schema from the target table 

4. **Selector Agent**:

    - The task of the selector agent is to find the target column wrt the user query & the schema data retrieved from the `Get Schema Tool`

    - If the target column is not found, then it goes to the `Interpretor Agent` to repeat its task

    - Else, it goes to `Scriber Agent`

4. **Scriber Agent**:

    - The task of the scriber agent is to write the SQL query baseed on the user query, target table & column table

4. **Verify Agent**:

    - The task of the verify agent is to check the SQL query if it is syntactically correct or not
    
    - Also it will check for DML statements (INSERT, UPDATE, DELETE, DROP etc.) in the SQL query

    - If any error is found in the SQL query, it will go to the `Scriber Agent` to regenerate the right query

    - Else it will go to the `Execute Tool`

4. **Execute Tool**:

    - This tool executes the SQL query in the database

    - If any error occured after execution, then it is sent to the `Scriber Agent` to regenerate the code

4. **Summary Agent**:

    - The task of the summary agent is to summarize the results given from the `Execute Tool` and the user query

---

## Tech Stack

### Frontend

- **React** : Chatbot UI

### Backend
   - **Langchain**
      - SQLDatabases Toolkit
      - Gemini LLM Integration
   
   - **Langgraph**
      - To build agent workflow

   - **Mermaid.Ink**
      - To visualize the workflow

   - **Mem0** (to be added)
      - To add memory to the agent

   - **MCP (Model Context Protocol)** (to be added)
      - Will be used to serve the agent via MCP

### Deployment
   - **Docker**
      - To containerize the agent
   - **K8S**
      - To manage containerized agents
   - **GCP** 
      - For hosting and scaling the application.
### Monitoring System
   - **Langfuse**
      - For tracking and storing agent trace logs
   - **Evaluation Pipeline**
      - To evaluate the performance of the agent
---