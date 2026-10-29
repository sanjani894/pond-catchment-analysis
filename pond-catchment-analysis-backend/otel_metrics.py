from prometheus_client import Counter, Histogram, make_asgi_app
from starlette.middleware.base import BaseHTTPMiddleware
from time import perf_counter

REQUESTS = Counter(
    "pond_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"]
)

DURATION = Histogram(
    "pond_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"]
)


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path

        if path == "/metrics":
            return await call_next(request)

        start = perf_counter()
        status = "500"

        try:
            response = await call_next(request)
            status = str(response.status_code)
            return response
        finally:
            elapsed = perf_counter() - start
            REQUESTS.labels(
                request.method, path, status
            ).inc()
            DURATION.labels(
                request.method, path
            ).observe(elapsed)


metrics_app = make_asgi_app()
