import requests
from datetime import datetime


PROMETHEUS_URL = "http://localhost:9090"

EXPECTED_SERVICES = [
    "user-service",
    "payment-service",
    "inventory-service"
]


# ============================================================
# Prometheus Query
# ============================================================

def query_prometheus(query):

    response = requests.get(
        f"{PROMETHEUS_URL}/api/v1/query",
        params={"query": query},
        timeout=10
    )

    response.raise_for_status()

    return response.json()


# ============================================================
# Check Service Availability
# ============================================================

def get_service_status():

    query = (
        'up{namespace="devops-ai",'
        'service=~"user-service|payment-service|inventory-service"}'
    )

    result = query_prometheus(query)

    results = result["data"]["result"]

    service_status = {}

    for item in results:

        metric = item["metric"]
        value = item["value"]

        service = metric.get("service")

        if service:
            service_status[service] = value[1]

    return service_status


# ============================================================
# Detect Incidents
# ============================================================

def detect_incidents(service_status):

    incidents = []

    for service in EXPECTED_SERVICES:

        # Service missing from Prometheus
        if service not in service_status:

            incident = {
                "service": service,
                "severity": "CRITICAL",
                "status": "DOWN",
                "reason": "Service is not available in Prometheus",
                "timestamp": datetime.now().isoformat()
            }

            incidents.append(incident)

        # Service exists but is DOWN
        elif service_status[service] != "1":

            incident = {
                "service": service,
                "severity": "CRITICAL",
                "status": "DOWN",
                "reason": "Prometheus reports service as DOWN",
                "timestamp": datetime.now().isoformat()
            }

            incidents.append(incident)

    return incidents


# ============================================================
# Display Incident
# ============================================================

def display_incident(incident):

    print("\n" + "=" * 60)
    print("INCIDENT DETECTED")
    print("=" * 60)

    print(f"\nService:   {incident['service']}")
    print(f"Severity:  {incident['severity']}")
    print(f"Status:    {incident['status']}")
    print(f"Reason:    {incident['reason']}")
    print(f"Timestamp: {incident['timestamp']}")

    print("\n" + "-" * 60)


# ============================================================
# Main
# ============================================================

def main():

    print("=" * 60)
    print("             INCIDENT DETECTOR")
    print("=" * 60)

    print("\nConnecting to Prometheus...")

    try:

        health_check = requests.get(
            f"{PROMETHEUS_URL}/-/healthy",
            timeout=5
        )

        health_check.raise_for_status()

        print("Prometheus connection: OK")

    except requests.RequestException as error:

        print(f"Prometheus connection failed: {error}")

        return

    # --------------------------------------------------------
    # Get service status
    # --------------------------------------------------------

    service_status = get_service_status()

    print("\nService status received from Prometheus.")

    # --------------------------------------------------------
    # Detect incidents
    # --------------------------------------------------------

    incidents = detect_incidents(service_status)

    # --------------------------------------------------------
    # Display result
    # --------------------------------------------------------

    if not incidents:

        print("\nNo incidents detected.")

        print("\nAll expected services are healthy.")

    else:

        print(f"\nIncidents detected: {len(incidents)}")

        for incident in incidents:

            display_incident(incident)

    print("\n" + "=" * 60)
    print("          INCIDENT CHECK COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    main()