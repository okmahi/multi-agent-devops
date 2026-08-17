from typing import Dict, Any


# ============================================================
# Diagnosis / RCA Agent
# ============================================================

def diagnosis_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Diagnosis / Root Cause Analysis Agent.

    Analyses:
    - Detected incidents
    - Monitoring data
    - Kubernetes evidence
    - Application logs

    Separates:
    - Confirmed incident condition
    - Supporting evidence
    - Possible causes
    - Root-cause confidence

    Important:
    Only evidence directly related to the detected incident
    is used when building the diagnosis.
    """

    print("\n[Diagnosis Agent]")
    print("Analysing incident evidence...")

    incidents = state.get(
        "incidents",
        []
    )

    evidence = state.get(
        "evidence",
        {}
    )

    monitoring_data = state.get(
        "monitoring_data",
        {}
    )

    # ========================================================
    # NO INCIDENT
    # ========================================================

    if not incidents:

        state["severity"] = "NORMAL"

        state["diagnosis"] = (
            "No significant incident detected."
        )

        state["root_cause"] = (
            "No root cause identified because no incident "
            "was detected."
        )

        state["diagnostic_evidence"] = {
            "confirmed_findings": [],
            "supporting_findings": [],
            "possible_causes": [],
            "confidence": "HIGH"
        }

        state.setdefault(
            "messages",
            []
        )

        state["messages"].append(
            "Root cause analysis completed: no incident."
        )

        print("\nSeverity: NORMAL")

        print(
            "\nDiagnosis:"
        )

        print(
            state["diagnosis"]
        )

        return state

    # ========================================================
    # DETERMINE HIGHEST SEVERITY
    # ========================================================

    severity_levels = {
        "NORMAL": 0,
        "WARNING": 1,
        "CRITICAL": 2
    }

    highest_severity = "NORMAL"

    for incident in incidents:

        severity = incident.get(
            "severity",
            "NORMAL"
        )

        if severity_levels.get(
            severity,
            0
        ) > severity_levels.get(
            highest_severity,
            0
        ):

            highest_severity = severity

    # ========================================================
    # IDENTIFY AFFECTED PODS
    # ========================================================

    incident_pods = {
        incident.get("pod")
        for incident in incidents
        if incident.get("pod")
    }

    # ========================================================
    # CONFIRMED FINDINGS
    # ========================================================

    confirmed_findings = []

    for incident in incidents:

        incident_type = incident.get(
            "type",
            "UNKNOWN"
        )

        pod = incident.get(
            "pod",
            "unknown"
        )

        value = incident.get(
            "value"
        )

        # ----------------------------------------------------
        # CPU INCIDENT
        # ----------------------------------------------------

        if incident_type == "CPU":

            if isinstance(
                value,
                (int, float)
            ):

                confirmed_findings.append(
                    f"Pod {pod} has critically high CPU "
                    f"usage of {value:.3f} cores."
                )

            else:

                confirmed_findings.append(
                    f"Pod {pod} has critically high CPU usage."
                )

        # ----------------------------------------------------
        # MEMORY INCIDENT
        # ----------------------------------------------------

        elif incident_type == "MEMORY":

            if isinstance(
                value,
                (int, float)
            ):

                confirmed_findings.append(
                    f"Pod {pod} has high memory usage "
                    f"of {value:.2f} MB."
                )

            else:

                confirmed_findings.append(
                    f"Pod {pod} has high memory usage."
                )

        # ----------------------------------------------------
        # OTHER INCIDENT
        # ----------------------------------------------------

        else:

            confirmed_findings.append(
                incident.get(
                    "message",
                    f"{incident_type} incident detected."
                )
            )

    # ========================================================
    # POD EVIDENCE
    #
    # Only inspect pods involved in the incident.
    # ========================================================

    supporting_findings = []

    pods = evidence.get(
        "pods",
        []
    )

    if isinstance(
        pods,
        list
    ):

        for pod in pods:

            pod_name = pod.get(
                "name",
                "unknown"
            )

            # ------------------------------------------------
            # Ignore unrelated pods
            # ------------------------------------------------

            if pod_name not in incident_pods:
                continue

            phase = pod.get(
                "phase",
                "Unknown"
            )

            restart_count = pod.get(
                "restart_count",
                0
            )

            # ------------------------------------------------
            # Pod state
            # ------------------------------------------------

            if phase != "Running":

                supporting_findings.append(
                    f"Affected pod {pod_name} "
                    f"is in {phase} state."
                )

            else:

                supporting_findings.append(
                    f"Affected pod {pod_name} "
                    f"is currently Running."
                )

            # ------------------------------------------------
            # Restart information
            # ------------------------------------------------

            if restart_count > 0:

                supporting_findings.append(
                    f"Affected pod {pod_name} "
                    f"has restarted {restart_count} time(s)."
                )

    # ========================================================
    # LOG EVIDENCE
    #
    # Only inspect logs for services related to the incident.
    # ========================================================

    logs = evidence.get(
        "logs",
        {}
    )

    log_errors = []

    if isinstance(
        logs,
        dict
    ):

        # ----------------------------------------------------
        # Derive affected services from incident pod names
        #
        # Example:
        # payment-service-77df... -> payment-service
        # ----------------------------------------------------

        affected_services = set()

        for incident in incidents:

            pod = incident.get(
                "pod"
            )

            if not pod:
                continue

            # Match known service naming convention.
            parts = pod.split("-")

            if len(parts) >= 3:

                service_name = "-".join(
                    parts[:-2]
                )

                affected_services.add(
                    service_name
                )

        for service, service_logs in logs.items():

            # Ignore unrelated service logs.
            if affected_services and service not in affected_services:
                continue

            if not isinstance(
                service_logs,
                str
            ):
                continue

            log_text = service_logs.lower()

            if any(
                keyword in log_text
                for keyword in [
                    "error",
                    "exception",
                    "failed",
                    "failure"
                ]
            ):

                log_errors.append(
                    f"{service} logs contain "
                    "error or failure messages."
                )

    supporting_findings.extend(
        log_errors
    )

    # ========================================================
    # DETERMINE POSSIBLE ROOT CAUSES
    # ========================================================

    possible_causes = []

    # --------------------------------------------------------
    # CPU incident
    # --------------------------------------------------------

    cpu_incident = any(
        incident.get("type") == "CPU"
        for incident in incidents
    )

    if cpu_incident:

        possible_causes.extend([
            "High application workload.",
            "CPU-intensive application processing.",
            "Insufficient CPU resources allocated to the pod."
        ])

    # --------------------------------------------------------
    # MEMORY incident
    # --------------------------------------------------------

    memory_incident = any(
        incident.get("type") == "MEMORY"
        for incident in incidents
    )

    if memory_incident:

        possible_causes.extend([
            "High application memory consumption.",
            "Memory-intensive workload.",
            "Insufficient memory resources allocated to the pod."
        ])

    # ========================================================
    # ROOT CAUSE CONFIDENCE
    # ========================================================

    if log_errors:

        confidence = "MODERATE"

    elif supporting_findings:

        confidence = "MODERATE"

    else:

        confidence = "LOW"

    # ========================================================
    # ROOT CAUSE STATEMENT
    #
    # Do NOT claim that a possible cause is confirmed.
    # ========================================================

    if confirmed_findings:

        root_cause = (
            "Confirmed incident condition: "
            + " ".join(
                confirmed_findings
            )
            + " "
            "The underlying cause cannot be confirmed "
            "from the available evidence."
        )

    else:

        root_cause = (
            "An incident was detected, but the available "
            "evidence is insufficient to determine the "
            "specific cause."
        )

    # ========================================================
    # DIAGNOSIS
    # ========================================================

    diagnosis = (
        f"Incident analysis completed with "
        f"{highest_severity} severity. "
        f"The detected condition is confirmed, but the "
        f"underlying cause requires further investigation."
    )

    # ========================================================
    # STORE RESULTS
    # ========================================================

    state["severity"] = highest_severity

    state["diagnosis"] = diagnosis

    state["root_cause"] = root_cause

    state["diagnostic_evidence"] = {

        "confirmed_findings": confirmed_findings,

        "supporting_findings": supporting_findings,

        "possible_causes": possible_causes,

        "confidence": confidence
    }

    state.setdefault(
        "messages",
        []
    )

    state["messages"].append(
        "Root cause analysis completed."
    )

    # ========================================================
    # OUTPUT
    # ========================================================

    print(
        f"\nSeverity: {highest_severity}"
    )

    print(
        "\nConfirmed Findings:"
    )

    for finding in confirmed_findings:

        print(
            f"- {finding}"
        )

    print(
        "\nSupporting Evidence:"
    )

    if supporting_findings:

        for finding in supporting_findings:

            print(
                f"- {finding}"
            )

    else:

        print(
            "- No additional supporting evidence."
        )

    print(
        "\nPossible Causes:"
    )

    if possible_causes:

        for cause in possible_causes:

            print(
                f"- {cause}"
            )

    else:

        print(
            "- No possible causes identified."
        )

    print(
        f"\nRoot Cause Confidence: {confidence}"
    )

    return state