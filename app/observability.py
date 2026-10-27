import logging
import json
import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

REQUESTS = Counter("http_requests_total", "HTTP requests", ["method", "path", "status"])
LATENCY = Histogram("http_request_duration_seconds", "HTTP request duration", ["method", "path"])

class RequestObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            path = request.url.path
            elapsed = time.perf_counter() - start
            if not path.startswith("/metrics"):
                REQUESTS.labels(request.method, path, str(status)).inc()
                LATENCY.labels(request.method, path).observe(elapsed)
            logging.info(json.dumps({"event":"http_request","request_id":request_id,
                "method":request.method,"path":path,"status":status,"duration_ms":round(elapsed*1000,2)}))

def metrics_response():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
