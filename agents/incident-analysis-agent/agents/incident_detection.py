import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ============================================================================
# INCIDENT DETECTION THRESHOLDS
# ============================================================================

THRESHOLDS = {
    "cpu": {
        "warning": 0.8,       # cores
        "critical": 1.5       # cores
    },
    "memory": {
        "warning": 1500,      # MB
        "critical": 2000      # MB
    },
    "availability": {
        "warning": 0.95,      # 95%
        "critical": 0.90      # 90%
    }
}


# ============================================================================
# VALUE PARSING HELPER
# ============================================================================

def extract_numeric_value(
    value: Any,
    preferred_keys: Optional[List[str]] = None
) -> float:
    """
    Convert monitoring values into a numeric float.

    Supports simple values:

        0.95

    and structured values:

        {"value": 0.95}

        {"value_mb": 85.0}

        {"availability": 0.95}
    """

    if isinstance(value, dict):

        keys = preferred_keys or [
            "value",
            "value_mb",
            "availability",
            "status"
        ]

        for key in keys:

            if key in value:

                return float(value[key])

        raise ValueError(
            f"No supported numeric field found in dictionary: {value}"
        )

    return float(value)


# ============================================================================
# EVALUATE MONITORING DATA
# ============================================================================

def evaluate_monitoring_data_for_incidents(
    monitoring_data: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Evaluate monitoring data against configured thresholds.

    Supported monitoring structure:

        cpu:
            {
                "pod-name": {
                    "value": 0.95,
                    "analysis": "..."
                }
            }

        memory:
            {
                "pod-name": {
                    "value_mb": 85.0,
                    "analysis": "..."
                }
            }

        services:
            {
                "payment-service": {
                    "status": "1",
                    "health": "UP",
                    "analysis": "..."
                }
            }

    Returns:
        List of incident dictionaries.
    """

    incidents: List[Dict[str, Any]] = []

    if not monitoring_data:

        logger.warning(
            "No monitoring data provided to evaluate"
        )

        return incidents

    logger.info(
        "Evaluating monitoring data for incidents..."
    )

    logger.debug(
        "Monitoring data keys: %s",
        list(monitoring_data.keys())
    )

    # ========================================================================
    # CPU EVALUATION
    # ========================================================================

    cpu_data = monitoring_data.get("cpu", {})

    if cpu_data:

        logger.debug(
            "Evaluating %d CPU metrics",
            len(cpu_data)
        )

        for pod_name, cpu_value in cpu_data.items():

            try:

                cpu_cores = extract_numeric_value(
                    cpu_value,
                    ["value"]
                )

                logger.debug(
                    "CPU for %s: %.3f cores",
                    pod_name,
                    cpu_cores
                )

                if cpu_cores >= THRESHOLDS["cpu"]["critical"]:

                    logger.warning(
                        "CRITICAL CPU detected on %s: %.3f cores",
                        pod_name,
                        cpu_cores
                    )

                    incidents.append(
                        {
                            "type": "CPU",
                            "pod": pod_name,
                            "severity": "CRITICAL",
                            "value": cpu_cores,
                            "message": (
                                f"{pod_name} CPU usage is critically high"
                            )
                        }
                    )

                elif cpu_cores >= THRESHOLDS["cpu"]["warning"]:

                    logger.warning(
                        "WARNING CPU detected on %s: %.3f cores",
                        pod_name,
                        cpu_cores
                    )

                    incidents.append(
                        {
                            "type": "CPU",
                            "pod": pod_name,
                            "severity": "WARNING",
                            "value": cpu_cores,
                            "message": (
                                f"{pod_name} CPU usage is high"
                            )
                        }
                    )

            except (ValueError, TypeError) as exc:

                logger.warning(
                    "Could not parse CPU value for %s: %s",
                    pod_name,
                    exc
                )

    # ========================================================================
    # MEMORY EVALUATION
    # ========================================================================

    memory_data = monitoring_data.get("memory", {})

    if memory_data:

        logger.debug(
            "Evaluating %d memory metrics",
            len(memory_data)
        )

        for pod_name, memory_value in memory_data.items():

            try:

                memory_mb = extract_numeric_value(
                    memory_value,
                    ["value_mb", "value"]
                )

                logger.debug(
                    "Memory for %s: %.2f MB",
                    pod_name,
                    memory_mb
                )

                if memory_mb >= THRESHOLDS["memory"]["critical"]:

                    logger.warning(
                        "CRITICAL memory detected on %s: %.2f MB",
                        pod_name,
                        memory_mb
                    )

                    incidents.append(
                        {
                            "type": "MEMORY",
                            "pod": pod_name,
                            "severity": "CRITICAL",
                            "value": memory_mb,
                            "message": (
                                f"{pod_name} memory usage is critically high"
                            )
                        }
                    )

                elif memory_mb >= THRESHOLDS["memory"]["warning"]:

                    logger.warning(
                        "WARNING memory detected on %s: %.2f MB",
                        pod_name,
                        memory_mb
                    )

                    incidents.append(
                        {
                            "type": "MEMORY",
                            "pod": pod_name,
                            "severity": "WARNING",
                            "value": memory_mb,
                            "message": (
                                f"{pod_name} memory usage is high"
                            )
                        }
                    )

            except (ValueError, TypeError) as exc:

                logger.warning(
                    "Could not parse memory value for %s: %s",
                    pod_name,
                    exc
                )

    # ========================================================================
    # SERVICE AVAILABILITY EVALUATION
    # ========================================================================

    services_data = monitoring_data.get("services", {})

    if services_data:

        logger.debug(
            "Evaluating %d service availability metrics",
            len(services_data)
        )

        for service_name, service_value in services_data.items():

            try:

                if isinstance(service_value, dict):

                    status = service_value.get(
                        "status",
                        "0"
                    )

                else:

                    status = service_value

                status_value = float(status)

                if status_value < 1:

                    logger.warning(
                        "CRITICAL availability detected on %s: status=%s",
                        service_name,
                        status
                    )

                    incidents.append(
                        {
                            "type": "AVAILABILITY",
                            "pod": service_name,
                            "severity": "CRITICAL",
                            "value": status_value,
                            "message": (
                                f"{service_name} availability is critically low"
                            )
                        }
                    )

            except (ValueError, TypeError) as exc:

                logger.warning(
                    "Could not parse availability value for %s: %s",
                    service_name,
                    exc
                )

    # ========================================================================
    # LEGACY AVAILABILITY EVALUATION
    # ========================================================================

    availability_data = monitoring_data.get(
        "availability",
        {}
    )

    if availability_data:

        logger.debug(
            "Evaluating %d availability metrics",
            len(availability_data)
        )

        for service_name, availability_value in availability_data.items():

            try:

                availability = extract_numeric_value(
                    availability_value,
                    ["value", "availability"]
                )

                if availability < THRESHOLDS["availability"]["critical"]:

                    logger.warning(
                        "CRITICAL availability on %s: %.3f",
                        service_name,
                        availability
                    )

                    incidents.append(
                        {
                            "type": "AVAILABILITY",
                            "pod": service_name,
                            "severity": "CRITICAL",
                            "value": availability,
                            "message": (
                                f"{service_name} availability is critically low"
                            )
                        }
                    )

                elif availability < THRESHOLDS["availability"]["warning"]:

                    logger.warning(
                        "WARNING availability on %s: %.3f",
                        service_name,
                        availability
                    )

                    incidents.append(
                        {
                            "type": "AVAILABILITY",
                            "pod": service_name,
                            "severity": "WARNING",
                            "value": availability,
                            "message": (
                                f"{service_name} availability is degraded"
                            )
                        }
                    )

            except (ValueError, TypeError) as exc:

                logger.warning(
                    "Could not parse availability value for %s: %s",
                    service_name,
                    exc
                )

    # ========================================================================
    # COMPLETION
    # ========================================================================

    logger.info(
        "Incident detection completed: %d incidents found",
        len(incidents)
    )

    return incidents


# ============================================================================
# INCIDENT DETECTION AGENT
# ============================================================================

def incident_detection_agent(
    state: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Incident Detection Agent.

    Evaluates monitoring_data and stores detected incidents in:

        state["incidents"]

    Supported detection types:

    - CPU
    - Memory
    - Service availability
    """

    logger.info(
        "=== INCIDENT DETECTION AGENT STARTED ==="
    )

    # ------------------------------------------------------------------------
    # Ensure messages exists
    # ------------------------------------------------------------------------

    state.setdefault(
        "messages",
        []
    )

    # ------------------------------------------------------------------------
    # Get monitoring data
    # ------------------------------------------------------------------------

    monitoring_data = state.get(
        "monitoring_data",
        {}
    )

    if not monitoring_data:

        logger.warning(
            "No monitoring data available in state"
        )

        state["incidents"] = []

        state["incident_detected"] = False

        state["messages"].append(
            "Incident Detection Agent: "
            "No monitoring data available."
        )

        logger.info(
            "=== INCIDENT DETECTION AGENT COMPLETED ==="
        )

        return state

    logger.info(
        "Monitoring data received: %s",
        list(monitoring_data.keys())
    )

    # ------------------------------------------------------------------------
    # Evaluate monitoring data
    # ------------------------------------------------------------------------

    incidents = evaluate_monitoring_data_for_incidents(
        monitoring_data
    )

    # ------------------------------------------------------------------------
    # Store incidents
    # ------------------------------------------------------------------------

    state["incidents"] = incidents

    # ------------------------------------------------------------------------
    # Update workflow status
    # ------------------------------------------------------------------------

    if incidents:

        logger.warning(
            "Incidents detected: %d",
            len(incidents)
        )

        incident_summary = ", ".join(
            f"{incident['type']} on {incident['pod']}"
            for incident in incidents
        )

        state["messages"].append(
            "Incident Detection Agent: "
            f"{len(incidents)} incidents detected "
            f"({incident_summary})."
        )

        state["incident_detected"] = True

    else:

        logger.info(
            "No incidents detected"
        )

        state["messages"].append(
            "Incident Detection Agent: "
            "No incidents detected."
        )

        state["incident_detected"] = False

    logger.info(
        "=== INCIDENT DETECTION AGENT COMPLETED ==="
    )

    return state
