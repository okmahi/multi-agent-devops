import requests
import subprocess
import json
from datetime import datetime


# ============================================================
# Configuration
# ============================================================

PROMETHEUS_URL = "http://localhost:9090"

NAMESPACE = "devops-ai"

SERVICES = [
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

    data = response.json()

    if data.get("status") != "success":
        raise RuntimeError(
            f"Prometheus query failed: {data}"
        )

    return data["data"]["result"]


# ============================================================
# Kubernetes Command
# ============================================================

def run_kubectl(command):

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return {
            "success": False,
            "error": result.stderr.strip()
        }

    return {
        "success": True,
        "output": result.stdout.strip()
    }


# ============================================================
# Collect Service Availability
# ============================================================

def collect_service_status():

    query = (
        'up{namespace="devops-ai",'
        'service=~"user-service|payment-service|inventory-service"}'
    )

    results = query_prometheus(query)

    services = {}

    for item in results:

        metric = item["metric"]

        service = metric.get("service")

        status = item["value"][1]

        if service:

            services[service] = {
                "status": "UP" if status == "1" else "DOWN",
                "value": status
            }

    return services


# ============================================================
# Collect CPU
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

    cpu = {}

    for item in results:

        pod = item["metric"].get("pod")

        value = float(item["value"][1])

        if pod:

            cpu[pod] = value

    return cpu


# ============================================================
# Collect Memory
# ============================================================

def collect_memory_usage():

    query = (
        'sum(container_memory_working_set_bytes{'
        'namespace="devops-ai",'
        'pod=~"user-service.*|payment-service.*|inventory-service.*"'
        '}) by (pod)'
    )

    results = query_prometheus(query)

    memory = {}

    for item in results:

        pod = item["metric"].get("pod")

        memory_bytes = float(item["value"][1])

        memory_mb = (
            memory_bytes / (1024 * 1024)
        )

        if pod:

            memory[pod] = memory_mb

    return memory


# ============================================================
# Collect Kubernetes Pods
# ============================================================

def collect_pods():

    command = [
        "kubectl",
        "get",
        "pods",
        "-n",
        NAMESPACE,
        "-o",
        "json"
    ]

    result = run_kubectl(command)

    if not result["success"]:

        return {
            "error": result["error"]
        }

    data = json.loads(result["output"])

    pods = []

    for item in data.get("items", []):

        metadata = item.get("metadata", {})
        status = item.get("status", {})

        pod_name = metadata.get("name")

        phase = status.get(
            "phase",
            "Unknown"
        )

        restart_count = 0

        for container in status.get(
            "containerStatuses",
            []
        ):

            restart_count += container.get(
                "restartCount",
                0
            )

        pods.append({
            "name": pod_name,
            "phase": phase,
            "restart_count": restart_count
        })

    return pods


# ============================================================
# Collect Kubernetes Events
# ============================================================

def collect_events():

    command = [
        "kubectl",
        "get",
        "events",
        "-n",
        NAMESPACE,
        "--sort-by=.lastTimestamp"
    ]

    result = run_kubectl(command)

    if not result["success"]:

        return {
            "error": result["error"]
        }

    return result["output"]


# ============================================================
# Collect Application Logs
# ============================================================

def collect_logs(service):

    command = [
        "kubectl",
        "logs",
        "-n",
        NAMESPACE,
        "-l",
        f"app={service}",
        "--tail=50"
    ]

    result = run_kubectl(command)

    if not result["success"]:

        return {
            "error": result["error"]
        }

    return result["output"]


# ============================================================
# Build Evidence Package
# ============================================================

def collect_evidence():

    print("\nCollecting incident evidence...")

    evidence = {

        "timestamp": datetime.utcnow().isoformat(),

        "namespace": NAMESPACE,

        "services": collect_service_status(),

        "cpu_usage": collect_cpu_usage(),

        "memory_usage": collect_memory_usage(),

        "kubernetes_pods": collect_pods(),

        "kubernetes_events": collect_events(),

        "application_logs": {}
    }

    for service in SERVICES:

        evidence["application_logs"][service] = (
            collect_logs(service)
        )

    return evidence


# ============================================================
# Display Evidence
# ============================================================

def display_evidence(evidence):

    print("\n" + "=" * 60)
    print("              INCIDENT EVIDENCE")
    print("=" * 60)

    # --------------------------------------------------------
    # Services
    # --------------------------------------------------------

    print("\n" + "-" * 60)
    print("SERVICE STATUS")
    print("-" * 60)

    for service, data in evidence["services"].items():

        print(
            f"{service}: {data['status']}"
        )

    # --------------------------------------------------------
    # CPU
    # --------------------------------------------------------

    print("\n" + "-" * 60)
    print("CPU USAGE")
    print("-" * 60)

    for pod, cpu in evidence["cpu_usage"].items():

        print(
            f"{pod}: {cpu:.6f} cores"
        )

    # --------------------------------------------------------
    # Memory
    # --------------------------------------------------------

    print("\n" + "-" * 60)
    print("MEMORY USAGE")
    print("-" * 60)

    for pod, memory in evidence["memory_usage"].items():

        print(
            f"{pod}: {memory:.2f} MB"
        )

    # --------------------------------------------------------
    # Kubernetes Pods
    # --------------------------------------------------------

    print("\n" + "-" * 60)
    print("KUBERNETES PODS")
    print("-" * 60)

    for pod in evidence["kubernetes_pods"]:

        print(
            f"{pod['name']} | "
            f"Phase: {pod['phase']} | "
            f"Restarts: {pod['restart_count']}"
        )

    # --------------------------------------------------------
    # Kubernetes Events
    # --------------------------------------------------------

    print("\n" + "-" * 60)
    print("KUBERNETES EVENTS")
    print("-" * 60)

    print(
        evidence["kubernetes_events"]
    )

    # --------------------------------------------------------
    # Logs
    # --------------------------------------------------------

    print("\n" + "-" * 60)
    print("APPLICATION LOGS")
    print("-" * 60)

    for service, logs in (
        evidence["application_logs"].items()
    ):

        print(
            f"\n[{service}]"
        )

        print(logs)

    print("\n" + "=" * 60)
    print("        EVIDENCE COLLECTION COMPLETED")
    print("=" * 60)


# ============================================================
# Main
# ============================================================

def main():

    print("=" * 60)
    print("           DEVOPS EVIDENCE COLLECTOR")
    print("=" * 60)

    print("\nChecking Prometheus...")

    try:

        response = requests.get(
            f"{PROMETHEUS_URL}/-/healthy",
            timeout=5
        )

        response.raise_for_status()

        print("Prometheus connection: OK")

    except requests.RequestException as error:

        print(
            f"Prometheus connection failed: {error}"
        )

        return

    try:

        evidence = collect_evidence()

        display_evidence(
            evidence
        )

    except Exception as error:

        print(
            f"\nEvidence collection failed: {error}"
        )


# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":
    main()