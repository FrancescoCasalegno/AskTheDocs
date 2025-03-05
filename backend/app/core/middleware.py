"""Middleware for processing application requests and responses."""
import uuid
from contextvars import ContextVar
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

job_id_contextvar: ContextVar[str] = ContextVar("job_id", default=None)


class JobIdMiddleware(BaseHTTPMiddleware):
    """Middleware class setting a unique job ID for each request."""

    async def dispatch(self, request: Request, call_next: Callable):
        """Run middleware logic."""
        # 1. Process the request
        request_id = str(uuid.uuid4())
        job_id_contextvar.set(request_id)

        # 2. Pass request to next middleware (or app router handler)
        response = await call_next(request)

        # 3. Process the response [not needed in our case]

        # 4. Return the response to the client
        return response
