import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.config import PROJECT_NAME, PROJECT_DESCRIPTION, VERSION, GENERATED_DIR
from app.database import Base, engine

# Setup structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("bulk_certificate_generator")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    logger.info("Initializing database tables and storage directories...")
    Base.metadata.create_all(bind=engine)
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Application startup complete.")
    yield
    # Shutdown actions
    logger.info("Application shutting down.")


app = FastAPI(
    title=PROJECT_NAME,
    description=PROJECT_DESCRIPTION,
    version=VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Custom validation error handler for friendly client responses
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        field_loc = " -> ".join(str(loc) for loc in err.get("loc", []))
        errors.append({
            "field": field_loc,
            "message": err.get("msg"),
            "type": err.get("type"),
        })
    logger.warning("Request validation failed on %s: %s", request.url.path, errors)
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error in request payload",
            "errors": errors,
        },
    )


# Global unhandled exception handler to prevent exposing raw stack traces
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled server exception at %s: %s", request.url.path, str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred while processing the request.",
        },
    )


# Health check endpoint
@app.get("/health", tags=["System"], summary="Health check endpoint")
def health_check():
    return {
        "status": "healthy",
        "service": PROJECT_NAME,
        "version": VERSION,
    }


@app.get("/", tags=["System"], summary="Root endpoint")
def root():
    return {
        "message": f"Welcome to {PROJECT_NAME}",
        "docs": "/docs",
        "health": "/health",
    }


# Include API routes
app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)

