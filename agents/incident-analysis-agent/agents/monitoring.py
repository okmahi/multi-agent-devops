from typing import Dict, Any

import sys
from pathlib import Path


# ============================================================
# Locate Phase 4 monitoring-agent directory
# ============================================================

PHASE4_DIR = Path(__file__).resolve().parent.parent.parent / "monitoring-agent"

if str(PHASE4_DIR) not in sys.path:
    sys.path.insert(0, str(PHASE4_DIR))


from monitoring_agent import (
    query_prometheus,
    analyse_service_health,
    analyse_cpu,
    analyse_memory,
    EXPECTED_SERVICES,
)


# ============================================================
# Monitoring Agent
# ============================================================

def monitoring_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Monitoring Agent

    Collects:
    - Service availability
    - CPU usage
    - Memory usage

    Uses the existing Phase 4 Prometheus monitoring logic.
    """

    print("\n[Monitoring Agent]")
    print("Checking service health and resource usage...")

    monitoring_data = {
        "services": {},
        "cpu": {},
        "memory": {},
    }

    # ========================================================
    # SERVICE AVAILABILITY
    # ========================================================

    service_query = (
        'up{namespace="devops-ai",'
        'service=~"user-service|payment-service|inventory-service"}'
    )

    service_result = query_prometheus(service_query)

    service_status = {}

    for item in service_result["data"]["result"]:

        metric = item["metric"]
        value = item["value"]

        service = metric.get("service")

        if service:
            service_status[service] = value[1]

    for service in EXPECTED_SERVICES:

        status = service_status.get(service, "0")

        monitoring_data["services"][service] = {
            "status": status,
            "health": (
                "UP"
                if status == "1"
                else "DOWN"
            ),
            "analysis": analyse_service_health(status),
        }

    # ========================================================
    # CPU USAGE
    # ========================================================

    cpu_query = (
        'sum(rate('
        'container_cpu_usage_seconds_total{'
        'namespace="devops-ai",'
        'pod=~"user-service.*|payment-service.*|inventory-service.*"'
        '}[5m])) by (pod)'
    )

    cpu_result = query_prometheus(cpu_query)

    for item in cpu_result["data"]["result"]:

        pod = item["metric"].get(
            "pod",
            "unknown"
        )

        cpu = float(item["value"][1])

        monitoring_data["cpu"][pod] = {
            "value": cpu,
            "analysis": analyse_cpu(cpu),
        }

    # ========================================================
    # MEMORY USAGE
    # ========================================================

    memory_query = (
        'sum(container_memory_working_set_bytes{'
        'namespace="devops-ai",'
        'pod=~"user-service.*|payment-service.*|inventory-service.*"'
        '}) by (pod)'
    )

    memory_result = query_prometheus(memory_query)

    for item in memory_result["data"]["result"]:

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

        monitoring_data["memory"][pod] = {
            "value_mb": memory_mb,
            "analysis": analyse_memory(memory_mb),
        }

    # ========================================================
    # STORE RESULTS
    # ========================================================

    state["monitoring_data"] = monitoring_data

    state["monitoring_completed"] = True

    state.setdefault("messages", [])

    state["messages"].append(
        "Monitoring completed successfully."
    )

    print("Monitoring data collected successfully.")

    return state