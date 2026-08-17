from typing import Dict, Any

import sys
import os


# ============================================================
# Import Existing Evidence Collector
# ============================================================

sys.path.append(
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "../../monitoring-agent"
        )
    )
)

from evidence_collector import (
    collect_service_status,
    collect_cpu_usage,
    collect_memory_usage,
    collect_pods,
    collect_events,
    collect_logs,
)


# ============================================================
# Evidence Agent
# ============================================================

def evidence_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evidence Collection Agent

    Collects supporting evidence for detected incidents:

    - Service status
    - CPU usage
    - Memory usage
    - Kubernetes pod status
    - Kubernetes events
    - Application logs

    The agent preserves incident information already
    collected by the Incident Detection Agent.
    """

    print("\n[Evidence Agent]")
    print("Collecting incident evidence...")

    # --------------------------------------------------------
    # Preserve incident information
    # --------------------------------------------------------

    incidents = state.get("incidents", [])

    state["incidents"] = incidents

    state["incident_detected"] = state.get(
        "incident_detected",
        bool(incidents)
    )

    # --------------------------------------------------------
    # Evidence container
    # --------------------------------------------------------

    evidence = {}

    # --------------------------------------------------------
    # 1. Service Status
    # --------------------------------------------------------

    try:

        evidence["services"] = collect_service_status()

    except Exception as error:

        evidence["services"] = {
            "error": str(error)
        }

    # --------------------------------------------------------
    # 2. CPU Usage
    # --------------------------------------------------------

    try:

        evidence["cpu"] = collect_cpu_usage()

    except Exception as error:

        evidence["cpu"] = {
            "error": str(error)
        }

    # --------------------------------------------------------
    # 3. Memory Usage
    # --------------------------------------------------------

    try:

        evidence["memory"] = collect_memory_usage()

    except Exception as error:

        evidence["memory"] = {
            "error": str(error)
        }

    # --------------------------------------------------------
    # 4. Kubernetes Pods
    # --------------------------------------------------------

    try:

        evidence["pods"] = collect_pods()

    except Exception as error:

        evidence["pods"] = {
            "error": str(error)
        }

    # --------------------------------------------------------
    # 5. Kubernetes Events
    # --------------------------------------------------------

    try:

        evidence["events"] = collect_events()

    except Exception as error:

        evidence["events"] = {
            "error": str(error)
        }

    # --------------------------------------------------------
    # 6. Application Logs
    # --------------------------------------------------------

    logs = {}

    services = [
        "user-service",
        "payment-service",
        "inventory-service"
    ]

    for service in services:

        try:

            logs[service] = collect_logs(service)

        except Exception as error:

            logs[service] = {
                "error": str(error)
            }

    evidence["logs"] = logs

    # --------------------------------------------------------
    # Store Evidence in LangGraph State
    # --------------------------------------------------------

    state["evidence"] = evidence

    state["evidence_collected"] = True

    state.setdefault(
        "messages",
        []
    )

    state["messages"].append(
        "Incident evidence collected successfully."
    )

    print("Evidence collection completed.")

    return state