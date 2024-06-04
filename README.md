# LangChain-FastAPI-Agent
This repository contains a Python-based LangChain agent that interacts with a SQLite database and various public APIs. The agent is exposed over a single FastAPI endpoint and can process natural language queries to decide whether to query the database or fetch data from a public API.
## Features
- **Database Querying**: Interacts with the Northwind SQLite database to retrieve information based on SQL queries.
- **Public API Integration**: Fetches data from a public API without authentication.
- **Authenticated API Integration**: Fetches data from a public API that requires authentication.
- **Natural Language Processing**: Determines the appropriate action (database query or API request) based on the input query.
- **FastAPI Endpoint**: Exposes the agent functionality over a FastAPI endpoint for easy interaction.
## Setup Instructions
1. **Clone the Repository**:
   bash
   git clone https://github.com/your-username/langchain-fastapi-agent.git
   cd langchain-fastapi-agent
   
2. **Download the Northwind Database**:
   sh
   curl -L -o northwind.db https://github.com/jpwhite3/northwind-SQLite3/blob/main/dist/northwind.db?raw=true
   
3. **Install Dependencies**:
   bash
   pip install fastapi uvicorn requests pydantic
   
4. **Run the FastAPI Server**:
   bash
   uvicorn agent_api:app --reload
   
5. **Test the API with Postman**:
   - Open Postman and create a new POST request to `http://127.0.0.1:8000/query`.
   - Set the request body to `raw` and `JSON`, for example:
     json
     {
         "query": "SELECT * FROM Customers"
     }
     
   - Send the request and view the response.
## Endpoints
- **POST /query**: Accepts a JSON payload with a query string. Determines whether to query the database or fetch data from a public API based on the input query.
## Example Queries
- **Database Query**:
  json
  {
      "query": "SELECT * FROM Customers"
  }
  
- **Public API Query**:
  json
  {
      "query": "Fetch data from public API"
  }
  
- **Authenticated API Query**:
  json
  {
      "query": "Fetch data from auth API"
  }
  
## Deployment
The application can be deployed to cloud platforms like Render or Vercel for wider accessibility.
## Demo
A demo video of the project interaction using Postman is available [here](#).
## License
This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.
