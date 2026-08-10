import requests


# ============================================================
# Configuration
# ============================================================

PROMETHEUS_URL = "http://localhost:9090"

EXPECTED_SERVICES = [
    "user-service",
    "payment-service",
    "inventory-service"
]

CPU_WARNING_THRESHOLD = 0.50
CPU_CRITICAL_THRESHOLD = 0.80

MEMORY_WARNING_THRESHOLD_MB = 100
MEMORY_CRITICAL_THRESHOLD_MB = 200


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

    data = response.json()

    if data.get("status") != "success":
        raise RuntimeError(
            f"Prometheus query failed: {data}"
        )

    return data["data"]["result"]


# ============================================================
# Service Health Detection
# ============================================================

def detect_service_incident(service, status):

    if status == "1":

        return {
            "service": service,
            "severity": "NORMAL",
            "status": "UP",
            "message": f"{service} is healthy"
        }

    return {
        "service": service,
        "severity": "CRITICAL",
        "status": "DOWN",
        "message": f"{service} is unavailable"
    }


# ============================================================
# CPU Incident Detection
# ============================================================

def detect_cpu_incident(pod, cpu):

    if cpu >= CPU_CRITICAL_THRESHOLD:

        return {
            "type": "CPU",
            "pod": pod,
            "severity": "CRITICAL",
            "value": cpu,
            "message": (
                f"{pod} CPU usage is critically high "
                f"({cpu:.3f} cores)"
            )
        }

    elif cpu >= CPU_WARNING_THRESHOLD:

        return {
            "type": "CPU",
            "pod": pod,
            "severity": "WARNING",
            "value": cpu,
            "message": (
                f"{pod} CPU usage is high "
                f"({cpu:.3f} cores)"
            )
        }

    return {
        "type": "CPU",
        "pod": pod,
        "severity": "NORMAL",
        "value": cpu,
        "message": (
            f"{pod} CPU usage is normal "
            f"({cpu:.3f} cores)"
        )
    }


# ============================================================
# Memory Incident Detection
# ============================================================

def detect_memory_incident(pod, memory_mb):

    if memory_mb >= MEMORY_CRITICAL_THRESHOLD_MB:

        return {
            "type": "MEMORY",
            "pod": pod,
            "severity": "CRITICAL",
            "value": memory_mb,
            "message": (
                f"{pod} memory usage is critically high "
                f"({memory_mb:.2f} MB)"
            )
        }

    elif memory_mb >= MEMORY_WARNING_THRESHOLD_MB:

        return {
            "type": "MEMORY",
            "pod": pod,
            "severity": "WARNING",
            "value": memory_mb,
            "message": (
                f"{pod} memory usage is high "
                f"({memory_mb:.2f} MB)"
            )
        }

    return {
        "type": "MEMORY",
        "pod": pod,
        "severity": "NORMAL",
        "value": memory_mb,
        "message": (
            f"{pod} memory usage is normal "
            f"({memory_mb:.2f} MB)"
        )
    }


# ============================================================
# Collect Service Status
# ============================================================

def collect_service_status():

    query = (
        'up{namespace="devops-ai",'
        'service=~"user-service|payment-service|inventory-service"}'
    )

    results = query_prometheus(query)

    service_status = {}

    for item in results:

        metric = item["metric"]
        value = item["value"]

        service = metric.get("service")

        if service:
            service_status[service] = value[1]

    return service_status


# ============================================================
# Collect CPU Usage
# ============================================================

def collect_cpu_usage():

    query = (
        'sum(rate('
        'container_cpu_usage_seconds_total{'
        'namespace="devops-ai",'
        'pod=~"user-service.*|payment-service.*|inventory-service.*"'
        '}[5m])) by (pod)'
    )

    results = query_prometheus(query)

    cpu_data = {}

    for item in results:

        pod = item["metric"].get("pod")

        if pod:
            cpu_data[pod] = float(item["value"][1])

    return cpu_data


# ============================================================
# Collect Memory Usage
# ============================================================

def collect_memory_usage():

    query = (
        'sum(container_memory_working_set_bytes{'
        'namespace="devops-ai",'
        'pod=~"user-service.*|payment-service.*|inventory-service.*"'
        '}) by (pod)'
    )

    results = query_prometheus(query)

    memory_data = {}

    for item in results:

        pod = item["metric"].get("pod")

        if pod:

            memory_bytes = float(item["value"][1])

            memory_mb = (
                memory_bytes / (1024 * 1024)
            )

            memory_data[pod] = memory_mb

    return memory_data


# ============================================================
# Incident Detection
# ============================================================

def detect_incidents():

    incidents = []

    # --------------------------------------------------------
    # Service availability
    # --------------------------------------------------------

    service_status = collect_service_status()

    for service in EXPECTED_SERVICES:

        status = service_status.get(service, "0")

        analysis = detect_service_incident(
            service,
            status
        )

        if analysis["severity"] == "CRITICAL":

            incidents.append(analysis)

    # --------------------------------------------------------
    # CPU
    # --------------------------------------------------------

    cpu_data = collect_cpu_usage()

    for pod, cpu in cpu_data.items():

        analysis = detect_cpu_incident(
            pod,
            cpu
        )

        if analysis["severity"] in [
            "WARNING",
            "CRITICAL"
        ]:

            incidents.append(analysis)

    # --------------------------------------------------------
    # Memory
    # --------------------------------------------------------

    memory_data = collect_memory_usage()

    for pod, memory_mb in memory_data.items():

        analysis = detect_memory_incident(
            pod,
            memory_mb
        )

        if analysis["severity"] in [
            "WARNING",
            "CRITICAL"
        ]:

            incidents.append(analysis)

    return incidents


# ============================================================
# Display Incident Report
# ============================================================

def display_incident_report(incidents):

    print("\n" + "=" * 60)
    print("              INCIDENT DETECTOR")
    print("=" * 60)

    if not incidents:

        print("\nNO INCIDENTS DETECTED")
        print("All monitored services and resources are healthy.")

        print("\n" + "=" * 60)

        return

    print(
        f"\nINCIDENTS DETECTED: {len(incidents)}"
    )

    print("\n" + "-" * 60)

    for number, incident in enumerate(
        incidents,
        start=1
    ):

        print(
            f"\nIncident #{number}"
        )

        print(
            f"Severity: {incident['severity']}"
        )

        if "service" in incident:

            print(
                f"Service: {incident['service']}"
            )

            print(
                f"Status: {incident['status']}"
            )

        elif incident["type"] == "CPU":

            print(
                f"Pod: {incident['pod']}"
            )

            print(
                f"CPU: {incident['value']:.6f} cores"
            )

        elif incident["type"] == "MEMORY":

            print(
                f"Pod: {incident['pod']}"
            )

            print(
                f"Memory: {incident['value']:.2f} MB"
            )

        print(
            f"Message: {incident['message']}"
        )

        print("-" * 60)


# ============================================================
# Main
# ============================================================

def main():

    print("=" * 60)
    print("          DEVOPS INCIDENT DETECTOR")
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

        print(
            f"Prometheus connection failed: {error}"
        )

        return

    try:

        incidents = detect_incidents()

        display_incident_report(
            incidents
        )

    except requests.RequestException as error:

        print(
            f"\nPrometheus query failed: {error}"
        )

    except Exception as error:

        print(
            f"\nIncident detection failed: {error}"
        )


# ============================================================
# Program Entry Point
# ============================================================

if __name__ == "__main__":
    main()