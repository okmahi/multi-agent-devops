from fastapi import FastAPI
import requests
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

# Instrument FastAPI
FastAPIInstrumentor.instrument_app(app)

# Instrument outgoing HTTP requests
RequestsInstrumentor().instrument()

@app.get("/")
def home():
    return {
        "service": "user-service",
        "status": "running"
    }

@app.get("/user/order")
def order():

    # Increment Prometheus counter
    REQUEST_COUNT.inc()

    logging.info("Order request received")

    payment_response = requests.get(
        "http://payment-service:8000/payment/process"
    )

    inventory_response = requests.get(
        "http://inventory-service:8000/inventory/check"
    )

    return {
        "message": "Order request received",
        "payment": payment_response.json(),
        "inventory": inventory_response.json()
    }

# Prometheus metrics endpoint
@app.get("/metrics")
def metrics():
    return Response(
        content=generate_latest(),
        media_type="text/plain"
    )