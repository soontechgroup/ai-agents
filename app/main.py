from fastapi import FastAPI

app = FastAPI(title="AI Agents API", version="1.0.0")

@app.get("/")
async def root():
    return {"message": "Welcome to AI Agents API"}