# ============= Curl commands =============

```md
# Basic health check

curl http://localhost:8000/health

# Test simple errors

curl http://localhost:8000/test/simple-error

# Test multiline data (this used to break!)

curl http://localhost:8000/test/multiline-data

# Test rich traceback with clickable paths

curl http://localhost:8000/test/exception-with-traceback

# Test file path logging

curl http://localhost:8000/test/file-path-logging

# Test nested exceptions

curl http://localhost:8000/test/nested-exception

# Test all log levels

curl http://localhost:8000/test/all-log-levels

# Test complex data structures

curl http://localhost:8000/test/dict-and-list-logging
```

---

# ============= TEST ENDPOINTS =============

```python




@app.get("/test/simple-error")
def test_simple_error():
    """Test basic error logging"""
    logger.warning("This is a warning message", user_id=None, action="test")
    logger.error("This is an error message", severity="high", request_id="test-123")
    return {"message": "Check your console for logs"}


@app.get("/test/multiline-data")
def test_multiline_data():
    """Test logging with newlines in data - this used to break!"""
    multiline_text = """This is line 1
This is line 2
This is line 3 with special chars: \n \t \r"""

    # Structured logging handles this gracefully
    logger.info(
        "Processing multiline content",
        content=multiline_text,
        lines=multiline_text.split("\n"),
        length=len(multiline_text),
    )

    return {"message": "Logged multiline data successfully"}


@app.get("/test/exception-with-traceback")
def test_exception_traceback():
    """Test full exception traceback with Rich formatting"""
    try:
        # Create a nested exception to show traceback
        def level_3():
            result = 10 / 0  # ZeroDivisionError
            return result

        def level_2():
            return level_3()

        def level_1():
            data = {"key": "value"}
            return level_2()

        level_1()
    except Exception as e:
        # exc_info=True triggers Rich traceback formatter
        logger.error(
            "Division by zero occurred", exc_info=True, function="test_exception_traceback", user_action="testing"
        )
        raise HTTPException(status_code=500, detail="Check console for rich traceback")


@app.get("/test/file-path-logging")
def test_file_path_logging():
    """Test logging file paths - used to cause newline issues"""
    import inspect

    frame = inspect.currentframe()
    if frame:
        filename = frame.f_code.co_filename
        lineno = frame.f_lineno
        function_name = frame.f_code.co_name

        # Log file location info - Rich makes these clickable in terminal!
        logger.debug(
            "Logging from specific location", file=filename, line=lineno, function=function_name, module=__name__
        )

    return {"message": "File path logged - check console (should be clickable!)"}


@app.get("/test/nested-exception")
def test_nested_exception():
    """Test exception chaining (exception raised from another exception)"""
    try:
        try:
            # First exception
            json_data = '{"invalid": json}'
            import json

            json.loads(json_data)
        except Exception as e:
            # Raise a new exception from the first one
            raise ValueError("Failed to parse configuration") from e
    except Exception as e:
        logger.critical("Configuration parsing failed", exc_info=True, config_source="test", attempted_data=json_data)
        raise HTTPException(status_code=500, detail="Check console for exception chain")


@app.get("/test/framework-filter")
def test_framework_filter():
    """Test that Starlette/FastAPI frames are filtered from traceback"""
    try:
        # This will raise an exception that goes through FastAPI's middleware
        1 / 0
    except Exception as e:
        logger.error("Error with framework stack", exc_info=True, note="Starlette/Uvicorn frames should be suppressed")
        raise HTTPException(status_code=500, detail="Check console - no framework noise!")


@app.get("/test/all-log-levels")
def test_all_log_levels():
    """Test all logging levels"""
    logger.debug("This is a DEBUG message", level="debug", timestamp=datetime.now())
    logger.info("This is an INFO message", level="info", timestamp=datetime.now())
    logger.warning("This is a WARNING message", level="warning", timestamp=datetime.now())
    logger.error("This is an ERROR message", level="error", timestamp=datetime.now())
    logger.critical("This is a CRITICAL message", level="critical", timestamp=datetime.now())

    return {"message": "All log levels tested - check console"}


@app.get("/test/dict-and-list-logging")
def test_complex_data():
    """Test logging complex data structures"""
    user_data = {
        "user_id": 12345,
        "name": "Test User",
        "permissions": ["read", "write", "admin"],
        "metadata": {"last_login": "2025-01-07", "ip": "192.168.1.1"},
    }

    logger.info(
        "User action recorded", user=user_data, action="login", success=True, tags=["authentication", "security"]
    )

    return {"message": "Complex data logged"}


# Startup event to verify logging works
@app.on_event("startup")
async def startup_event():
    logger.info(
        "Application starting", app_title=app_title, app_version=app_version, log_level=os.getenv("LOG_LEVEL", "INFO")
    )


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutting down gracefully")
```
