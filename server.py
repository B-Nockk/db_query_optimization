# serve.py
import uvicorn
from main import app, config
from app.api.v1 import patient_router

# Mount all routers here
app.include_router(patient_router)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",  # Points to the app instance
        host="0.0.0.0",
        port=8080,
        reload=config.environment != "production",
        log_level=config.logging.level_value.lower(),
    )
