import os
from fastapi import FastAPI, HTTPException, Request, Depends, Header
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
from google_auth_oauthlib.flow import Flow
import logging
from dotenv import load_dotenv
from fastapi.security import OAuth2PasswordBearer
import requests
from langchain_community.utilities import SQLDatabase
from langchain_openai import OpenAI
from langchain.prompts import PromptTemplate
from langchain_community.tools import DuckDuckGoSearchRun
from langchain.chains import LLMChain
import sqlite3

# Load environment variables from .env file
load_dotenv()
# Set environment variable to allow insecure transport for OAuth
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Google OAuth Configuration
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:8000/oauth-callback"
SCOPE = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile"
]
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

# OAuth2 Bearer token scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Initialize OpenAI LLM
llm = OpenAI(temperature=0)

# Connect to SQLite database
db = SQLDatabase.from_uri("sqlite:///northwind.db")

# Get table information and names
table_info = db.get_table_info()
table_names = db.get_usable_table_names()

print("Table Info:", table_info)
print("Table Names:", table_names)

# Create a mapping dictionary for case-insensitivity
case_mapping = {name.lower(): name for name in table_names}
print("Case Mapping:", case_mapping)

# Create a prompt for SQL queries
sql_prompt = PromptTemplate(
    input_variables=["query", "table_info", "table_names"],
    template="""Given the following SQLite tables and their schemas (note: table and column names are case-sensitive): {table_info}

Available table names (use EXACTLY these names, they are case-sensitive):
{table_names}

Write a SQLite query to answer the following question: {query}

Make sure to:
1. Use EXACTLY the table names as provided in the list above (case-sensitive).
2. Use proper JOIN conditions when combining tables.
3. Use appropriate aggregations (SUM, COUNT, AVG) and sorting (ORDER BY) when needed.
4. Use meaningful column aliases (AS) for readability.

SQLite Query:"""
)

# Create LLMChain for SQL queries
sql_chain = LLMChain(llm=llm, prompt=sql_prompt, verbose=True)

# Initialize DuckDuckGo search tool
search_tool = DuckDuckGoSearchRun()

# Create prompt for general queries
general_prompt = PromptTemplate(
    input_variables=["question", "search_result"],
    template="""Question: {question}
Answer: Let's find out using a web search.
{search_result}
Based on the search result, the answer is:
"""
)

class QueryRequest(BaseModel):
    query: str
    class Config:
        schema_extra = {
            "example": {
                "query": "What is the total revenue from orders in the Northwind database?"
            }
        }

def fix_case(sql_query):
    for lowercase, original in case_mapping.items():
        sql_query = sql_query.replace(lowercase, original)
    return sql_query

@app.get("/")
async def root():
    return {"message": "Hello from the Langchain Agent API!"}

@app.get("/tables")
async def get_table_names():
    """Endpoint to directly list all table names in the database."""
    return {"table_names": table_names}

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        response = requests.get("https://www.googleapis.com/oauth2/v1/userinfo", headers={"Authorization": f"Bearer {token}"})
        response.raise_for_status()
        user_info = response.json()
        return user_info
    except Exception as e:
        logger.error(f"Error fetching user info: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@app.post("/query")
async def query_agent(request: QueryRequest, user: dict = Depends(get_current_user)):
    try:
        print("Original Query:", request.query)
        
        # Direct handling for queries about table names
        if any(phrase in request.query.lower() for phrase in ["list all table names", "what are the table names", "show table names"]):
            return {"result": f"The tables in the Northwind database are: {', '.join(table_names)}."}
        
        # Check if the query is about the Northwind database
        if any(keyword in request.query.lower() for keyword in ["northwind"] + [name.lower() for name in table_names]):
            # Generate SQL query
            sql_query = sql_chain.run(query=request.query, table_info=table_info, table_names="\n".join(table_names))
            print("Generated SQL Query:", sql_query)

            # Fix case in the generated SQL query
            sql_query_fixed = fix_case(sql_query)
            print("Fixed Case SQL Query:", sql_query_fixed)

            # Execute SQL query
            result = db.run(sql_query_fixed)
        else:
            search_result = search_tool.run(request.query)
            # Use OpenAI directly for summarizing the search result
            summary_prompt = general_prompt.format(question=request.query, search_result=search_result)
            result = llm(summary_prompt)

        return {"result": result, "user": user}
    except Exception as e:
        print("Error:", str(e))
        if isinstance(e, sqlite3.OperationalError) and "no such table:" in str(e):
            table_name = str(e).split("no such table: ")[1].split()[0]
            raise HTTPException(status_code=500, detail=f"Table '{table_name}' not found in the database. Available tables are: {', '.join(table_names)}")
        else:
            raise HTTPException(status_code=500, detail=str(e))

# Google OAuth Flow Initialization
flow = Flow.from_client_config(
    client_config={
        "web": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": GOOGLE_AUTH_URL,
            "token_uri": GOOGLE_TOKEN_URL,
            "redirect_uris": [REDIRECT_URI],
        }
    },
    scopes=SCOPE
)
flow.redirect_uri = REDIRECT_URI

@app.get("/login")
async def login_via_google():
    authorization_url, _ = flow.authorization_url(prompt="consent")
    return RedirectResponse(url=authorization_url)

@app.get("/oauth-callback")
async def oauth_callback(request: Request):
    try:
        logger.info(f"Fetching token for authorization response: {request.url}")
        flow.fetch_token(authorization_response=str(request.url))
    except Exception as e:
        logger.error(f"Error fetching token: {e}")
        raise HTTPException(status_code=400, detail="Token fetching failed")
    
    credentials = flow.credentials
    if not credentials:
        logger.error("Failed to obtain credentials")
        raise HTTPException(status_code=500, detail="Failed to obtain credentials")
    
    return {
        "message": "Successfully logged in via Google",
        "access_token": credentials.token,
        "refresh_token": credentials.refresh_token
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)