import requests

PROMETHEUS_URL = "http://localhost:9090"

EXPECTED_SERVICES = [
    "user-service",
    "payment-service",
    "inventory-service"
]


# ============================================================
# Prometheus Query Function
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
# Service Health Analysis
# ============================================================

def analyse_service_health(status):

    if status == "1":
        return "HEALTHY"
    else:
        return "CRITICAL"


# ============================================================
# CPU Analysis
# ============================================================

def analyse_cpu(cpu):

    if cpu > 0.80:
        return "CRITICAL"

    elif cpu > 0.50:
        return "WARNING"

    else:
        return "NORMAL"


# ============================================================
# Memory Analysis
# ============================================================

def analyse_memory(memory_mb):

    if memory_mb > 200:
        return "CRITICAL"

    elif memory_mb > 100:
        return "WARNING"

    else:
        return "NORMAL"


# ============================================================
# Main Monitoring Agent
# ============================================================

def main():

    print("=" * 60)
    print("             DEVOPS MONITORING AGENT")
    print("=" * 60)

    print("\nConnecting to Prometheus...")

    # --------------------------------------------------------
    # 1. Check Prometheus connection
    # --------------------------------------------------------

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
    # 2. Service Availability
    # --------------------------------------------------------

    query = (
        'up{namespace="devops-ai",'
        'service=~"user-service|payment-service|inventory-service"}'
    )

    result = query_prometheus(query)

    results = result["data"]["result"]

    # Store Prometheus results
    service_status = {}

    for item in results:

        metric = item["metric"]
        value = item["value"]

        service = metric.get("service")

        if service:

            service_status[service] = value[1]

    print("\n" + "-" * 60)
    print("SERVICE AVAILABILITY")
    print("-" * 60)

    print(f"\nExpected services: {len(EXPECTED_SERVICES)}")

    # Check every expected service
    for service in EXPECTED_SERVICES:

        # ----------------------------------------------------
        # Service exists in Prometheus
        # ----------------------------------------------------

        if service in service_status:

            status = service_status[service]

            if status == "1":

                health = "UP"

            else:

                health = "DOWN"

            analysis = analyse_service_health(status)

        # ----------------------------------------------------
        # Service missing from Prometheus
        # ----------------------------------------------------

        else:

            health = "DOWN"
            analysis = "CRITICAL"

        print(f"\nService: {service}")
        print(f"Status:  {health}")
        print(f"Analysis: {analysis}")

    # --------------------------------------------------------
    # 3. CPU Usage
    # --------------------------------------------------------

    cpu_query = (
        'sum(rate('
        'container_cpu_usage_seconds_total{'
        'namespace="devops-ai",'
        'pod=~"user-service.*|payment-service.*|inventory-service.*"'
        '}[5m])) by (pod)'
    )

    cpu_result = query_prometheus(cpu_query)

    cpu_results = cpu_result["data"]["result"]

    print("\n" + "-" * 60)
    print("CPU USAGE")
    print("-" * 60)

    if not cpu_results:

        print("\nNo CPU metrics available.")

    else:

        for item in cpu_results:

            pod = item["metric"].get(
                "pod",
                "unknown"
            )

            cpu = float(item["value"][1])

            analysis = analyse_cpu(cpu)

            print(f"\nPod: {pod}")
            print(f"CPU: {cpu:.6f} cores")
            print(f"Analysis: {analysis}")

    # --------------------------------------------------------
    # 4. Memory Usage
    # --------------------------------------------------------

    memory_query = (
        'sum(container_memory_working_set_bytes{'
        'namespace="devops-ai",'
        'pod=~"user-service.*|payment-service.*|inventory-service.*"'
        '}) by (pod)'
    )

    memory_result = query_prometheus(memory_query)

    memory_results = memory_result["data"]["result"]

    print("\n" + "-" * 60)
    print("MEMORY USAGE")
    print("-" * 60)

    if not memory_results:

        print("\nNo memory metrics available.")

    else:

        for item in memory_results:

            pod = item["metric"].get(
                "pod",
                "unknown"
            )

            memory_bytes = float(
                item["value"][1]
            )

            memory_mb = (
                memory_bytes /
                (1024 * 1024)
            )

            analysis = analyse_memory(memory_mb)

            print(f"\nPod: {pod}")
            print(f"Memory: {memory_mb:.2f} MB")
            print(f"Analysis: {analysis}")

    # --------------------------------------------------------
    # 5. Monitoring Summary
    # --------------------------------------------------------

    print("\n" + "-" * 60)
    print("MONITORING SUMMARY")
    print("-" * 60)

    healthy_services = []
    critical_services = []

    for service in EXPECTED_SERVICES:

        if service not in service_status:

            critical_services.append(service)

        elif service_status[service] == "1":

            healthy_services.append(service)

        else:

            critical_services.append(service)

    print(f"\nHealthy services: {len(healthy_services)}")
    print(f"Critical services: {len(critical_services)}")

    if critical_services:

        print("\nINCIDENT DETECTED")

        for service in critical_services:

            print(
                f"CRITICAL: {service} is unavailable"
            )

    else:

        print("\nNo service availability incidents detected.")

    # --------------------------------------------------------
    # 6. Finished
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("          MONITORING CHECK COMPLETED")
    print("=" * 60)


# ============================================================
# Program Entry Point
# ============================================================

if __name__ == "__main__":
    main()