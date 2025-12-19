from fastapi import FastAPI
from pydantic import BaseModel
from orchestrator import Orchestrator

app = FastAPI()
orchestrator = Orchestrator()

class QueryRequest(BaseModel):
    query: str
    propertyId: str = None # Required for GA4

@app.post("/query")
async def query_endpoint(request: QueryRequest):
    # Requirement: propertyId is required for GA4-only queries
    if not request.query:
        return {"response": "Please provide a query."}
        
    try:
        response = await orchestrator.handle_query(request.query, request.propertyId)
        return {"response": response}
    except Exception as e:
        # Prevent the server from crashing; return a clean error
        return {"response": f"An internal error occurred: {str(e)}"}