from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import sqlite3
import requests
import json

app = FastAPI()

# Database connection
def get_db_connection():
    conn = sqlite3.connect('northwind.db')
    conn.row_factory = sqlite3.Row
    return conn

# Public API example without authentication
public_api_url = "https://restful-api.dev/"

# Example API that requires authentication
auth_api_url = "https://example.com/auth-required-api"
auth_token = "your_auth_token_here"  # Replace with your actual token

class QueryRequest(BaseModel):
    query: str

def query_northwind_db(query: str):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(query)
        rows = cur.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()

def fetch_public_api():
    response = requests.get(public_api_url)
    if response.status_code == 200:
        return response.json()
    else:
        raise HTTPException(status_code=response.status_code, detail="Failed to fetch from public API")

def fetch_auth_api():
    headers = {
        "Authorization": f"Bearer {auth_token}"
    }
    response = requests.get(auth_api_url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        raise HTTPException(status_code=response.status_code, detail="Failed to fetch from authenticated API")

@app.post("/query")
async def handle_query(request: QueryRequest):
    query = request.query.lower()

    if "select" in query and "from" in query:
        return query_northwind_db(query)
    elif "public api" in query:
        return fetch_public_api()
    elif "auth api" in query:
        return fetch_auth_api()
    else:
        raise HTTPException(status_code=400, detail="Query not recognized")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
