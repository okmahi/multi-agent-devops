from typing import Dict, Any


def recommendation_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recommendation Agent

    Generates incident-specific remediation recommendations
    based on:
    - Incident severity
    - Detected incidents
    - Root cause
    - Evidence
    """

    print("\n[Recommendation Agent]")
    print("Generating recommended action...")

    severity = state.get("severity", "NORMAL")
    incidents = state.get("incidents", [])
    root_cause = state.get(
        "root_cause",
        "No significant problem detected."
    )

    # --------------------------------------------------------
    # No incident
    # --------------------------------------------------------

    if not incidents or severity == "NORMAL":

        recommendation = (
            "No action required. Continue normal monitoring."
        )

    else:

        recommendations = []

        # ----------------------------------------------------
        # Analyse each incident
        # ----------------------------------------------------

        for incident in incidents:

            incident_type = incident.get("type")

            # ------------------------------------------------
            # CPU incident
            # ------------------------------------------------

            if incident_type == "CPU":

                pod = incident.get(
                    "pod",
                    "unknown"
                )

                cpu = incident.get(
                    "value",
                    0
                )

                recommendations.append(
                    f"Investigate high CPU usage on {pod} "
                    f"({cpu:.3f} cores)."
                )

                recommendations.append(
                    "Check the application's workload and "
                    "recent deployment changes."
                )

                recommendations.append(
                    "Review CPU requests and limits for the "
                    "affected deployment."
                )

                recommendations.append(
                    "Check application logs for errors, "
                    "exceptions or unusually expensive operations."
                )

                recommendations.append(
                    "If high CPU usage persists, consider "
                    "scaling the affected service."
                )

            # ------------------------------------------------
            # Memory incident
            # ------------------------------------------------

            elif incident_type == "MEMORY":

                pod = incident.get(
                    "pod",
                    "unknown"
                )

                memory = incident.get(
                    "value",
                    0
                )

                recommendations.append(
                    f"Investigate high memory usage on {pod} "
                    f"({memory:.2f} MB)."
                )

                recommendations.append(
                    "Check for memory leaks or unusually "
                    "large workloads."
                )

                recommendations.append(
                    "Review Kubernetes memory requests and limits."
                )

                recommendations.append(
                    "Check whether the pod has experienced "
                    "recent restarts or OOM events."
                )

                recommendations.append(
                    "Consider increasing replicas or memory "
                    "allocation if the condition persists."
                )

            # ------------------------------------------------
            # Service availability incident
            # ------------------------------------------------

            elif "service" in incident:

                service = incident.get(
                    "service",
                    "unknown"
                )

                status = incident.get(
                    "status",
                    "DOWN"
                )

                recommendations.append(
                    f"Investigate why {service} is unavailable "
                    f"(status: {status})."
                )

                recommendations.append(
                    "Check the Kubernetes pod status, "
                    "deployment and recent events."
                )

                recommendations.append(
                    "Review application logs for startup "
                    "or runtime failures."
                )

                recommendations.append(
                    "Restart or redeploy the service only "
                    "after identifying the underlying problem."
                )

            # ------------------------------------------------
            # Unknown incident
            # ------------------------------------------------

            else:

                recommendations.append(
                    "Investigate the detected incident using "
                    "Kubernetes status, metrics, logs and traces."
                )

        # ----------------------------------------------------
        # Severity-specific guidance
        # ----------------------------------------------------

        if severity == "CRITICAL":

            recommendations.insert(
                0,
                "CRITICAL incident: immediate investigation "
                "is required."
            )

        elif severity == "WARNING":

            recommendations.insert(
                0,
                "WARNING condition: investigate the issue "
                "and continue monitoring closely."
            )

        # ----------------------------------------------------
        # Add root-cause context
        # ----------------------------------------------------

        recommendations.append(
            f"Current diagnosis: {root_cause}"
        )

        recommendation = "\n".join(
            f"{index}. {action}"
            for index, action in enumerate(
                recommendations,
                start=1
            )
        )

    # --------------------------------------------------------
    # Store recommendation
    # --------------------------------------------------------

    state["recommendation"] = recommendation

    state.setdefault(
        "messages",
        []
    )

    state["messages"].append(
        "Recommended action generated."
    )

    print(
        f"\nSeverity:\n{severity}"
    )

    print(
        f"\nRecommended Action:\n{recommendation}"
    )

    return state