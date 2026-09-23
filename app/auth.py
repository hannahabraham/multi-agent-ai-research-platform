from fastapi import Request, HTTPException


async def require_api_key(request: Request) -> None:
    """Validate the X-API-Key header when API-key auth is configured."""

    config = request.app.state.config
    if not config.api_key:
        return  # auth disabled when no key is configured
    key = request.headers.get("X-API-Key", "")
    if key != config.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")
