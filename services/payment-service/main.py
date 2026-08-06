from fastapi import FastAPI
import logging
import tracing

from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

from prometheus_client import Counter, generate_latest
from fastapi.responses import Response

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

app = FastAPI()

# Prometheus Counter
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests"
)

# OpenTelemetry Instrumentation
FastAPIInstrumentor.instrument_app(app)
RequestsInstrumentor().instrument()

@app.get("/")
def home():
    return {
        "service": "payment-service",
        "status": "running"
    }

@app.get("/payment/process")
def process_payment():

    # Increment Prometheus counter
    REQUEST_COUNT.inc()

    logging.info("Payment processed")

    return {
        "status": "payment successful"
    }

# Prometheus Metrics Endpoint
@app.get("/metrics")
def metrics():
    return Response(
        content=generate_latest(),
        media_type="text/plain"
    )