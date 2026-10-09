def success_response(message: str, data: object | None = None) -> dict:
    """Every successful response looks like {"success": true, "message": ..., "data": ...}."""
    return {"success": True, "message": message, "data": data}
