from langgraph.graph import StateGraph, END

from graph.workflow import DevOpsState

from agents.diagnosis import diagnosis_agent
from agents.recommendation import recommendation_agent
from agents.ai_analysis import ai_analysis_agent
from agents.remediation import remediation_agent
from agents.verification import verification_agent


# ============================================================
# SIMULATED EVIDENCE AGENT
# ============================================================

def simulated_evidence_agent(state):
    """
    Simulated evidence collector used for end-to-end testing.

    This does NOT query Prometheus or Kubernetes.

    It provides deterministic evidence so that the complete
    incident-response pipeline can be tested safely.
    """

    print("\n" + "=" * 60)
    print("STEP 1: EVIDENCE COLLECTION")
    print("=" * 60)

    print("\n[Evidence Agent]")
    print("Using simulated incident evidence...")

    # --------------------------------------------------------
    # Simulated evidence
    # --------------------------------------------------------

    state["evidence"] = {

        # ----------------------------------------------------
        # Service status
        # ----------------------------------------------------

        "services": {
            "payment-service": {
                "status": "UP",
                "value": "1"
            }
        },

        # ----------------------------------------------------
        # CPU
        # ----------------------------------------------------

        "cpu": {
            "payment-service-test": 0.95
        },

        # ----------------------------------------------------
        # Memory
        # ----------------------------------------------------

        "memory": {
            "payment-service-test": 85.0
        },

        # ----------------------------------------------------
        # Kubernetes pod
        # ----------------------------------------------------

        "pods": [
            {
                "name": "payment-service-test",
                "phase": "Running",
                "restart_count": 0
            }
        ],

        # ----------------------------------------------------
        # Kubernetes events
        # ----------------------------------------------------

        "events": (
            "Normal Started payment-service-test "
            "Container started successfully."
        ),

        # ----------------------------------------------------
        # Application logs
        # ----------------------------------------------------

        "logs": {
            "payment-service": (
                "ERROR: CPU processing failure"
            )
        }
    }

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


# ============================================================
# BUILD COMPLETE INCIDENT TEST WORKFLOW
# ============================================================

def build_incident_test_workflow():

    workflow = StateGraph(
        DevOpsState
    )

    # ========================================================
    # ADD AGENTS
    # ========================================================

    workflow.add_node(
        "evidence",
        simulated_evidence_agent
    )

    workflow.add_node(
        "diagnosis",
        diagnosis_agent
    )

    workflow.add_node(
        "recommendation",
        recommendation_agent
    )

    workflow.add_node(
        "ai_analysis",
        ai_analysis_agent
    )

    workflow.add_node(
        "remediation",
        remediation_agent
    )

    workflow.add_node(
        "verification",
        verification_agent
    )

    # ========================================================
    # ENTRY
    # ========================================================

    workflow.set_entry_point(
        "evidence"
    )

    # ========================================================
    # EVIDENCE → DIAGNOSIS
    # ========================================================

    workflow.add_edge(
        "evidence",
        "diagnosis"
    )

    # ========================================================
    # DIAGNOSIS → RECOMMENDATION
    # ========================================================

    workflow.add_edge(
        "diagnosis",
        "recommendation"
    )

    # ========================================================
    # RECOMMENDATION → AI ANALYSIS
    # ========================================================

    workflow.add_edge(
        "recommendation",
        "ai_analysis"
    )

    # ========================================================
    # AI ANALYSIS → REMEDIATION
    # ========================================================

    workflow.add_edge(
        "ai_analysis",
        "remediation"
    )

    # ========================================================
    # REMEDIATION → VERIFICATION
    # ========================================================

    workflow.add_edge(
        "remediation",
        "verification"
    )

    # ========================================================
    # VERIFICATION → END
    #
    # This test executes the complete path once.
    # The production workflow in graph/workflow.py contains
    # the retry routing logic.
    # ========================================================

    workflow.add_edge(
        "verification",
        END
    )

    return workflow.compile()


# ============================================================
# DISPLAY FINAL RESULTS
# ============================================================

def display_results(state):
    """
    Display the important results from every agent.
    """

    print("\n" + "=" * 60)
    print("FINAL INCIDENT RESPONSE RESULTS")
    print("=" * 60)

    # --------------------------------------------------------
    # Incident
    # --------------------------------------------------------

    print("\n[INCIDENT]")

    for incident in state.get(
        "incidents",
        []
    ):

        print(
            f"Type: {incident.get('type')}"
        )

        print(
            f"Pod: {incident.get('pod')}"
        )

        print(
            f"Severity: {incident.get('severity')}"
        )

        print(
            f"Value: {incident.get('value')}"
        )

        print(
            f"Message: {incident.get('message')}"
        )

    # --------------------------------------------------------
    # Diagnosis
    # --------------------------------------------------------

    print("\n[DIAGNOSIS]")

    diagnosis = state.get(
        "diagnosis"
    )

    print(
        diagnosis
    )

    diagnostic_evidence = state.get(
        "diagnostic_evidence",
        {}
    )

    print("\nConfirmed Findings:")

    for finding in diagnostic_evidence.get(
        "confirmed_findings",
        []
    ):

        print(
            f"- {finding}"
        )

    print("\nSupporting Findings:")

    for finding in diagnostic_evidence.get(
        "supporting_findings",
        []
    ):

        print(
            f"- {finding}"
        )

    print("\nPossible Causes:")

    for cause in diagnostic_evidence.get(
        "possible_causes",
        []
    ):

        print(
            f"- {cause}"
        )

    print(
        "\nRoot Cause Confidence: "
        f"{diagnostic_evidence.get('confidence', 'UNKNOWN')}"
    )

    # --------------------------------------------------------
    # Recommendation
    # --------------------------------------------------------

    print("\n[RECOMMENDATION]")

    print(
        state.get(
            "recommendation",
            "No recommendation available."
        )
    )

    # --------------------------------------------------------
    # AI Analysis
    # --------------------------------------------------------

    print("\n[AI ANALYSIS]")

    print(
        state.get(
            "ai_analysis",
            "No AI analysis available."
        )
    )

    # --------------------------------------------------------
    # Remediation
    # --------------------------------------------------------

    print("\n[REMEDIATION]")

    remediation = state.get(
        "remediation_results",
        state.get(
            "remediation",
            {}
        )
    )

    print(
        remediation
    )

    # --------------------------------------------------------
    # Verification
    # --------------------------------------------------------

    print("\n[VERIFICATION]")

    verification = state.get(
        "verification",
        {}
    )

    print(
        f"Status: "
        f"{verification.get('status', 'UNKNOWN')}"
    )

    print(
        f"Result: "
        f"{verification.get('result', 'UNKNOWN')}"
    )

    print(
        f"Confidence: "
        f"{verification.get('confidence', 'UNKNOWN')}"
    )

    # --------------------------------------------------------
    # Messages
    # --------------------------------------------------------

    print("\n[WORKFLOW MESSAGES]")

    for message in state.get(
        "messages",
        []
    ):

        print(
            f"- {message}"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("       DEVOPS COMPLETE INCIDENT PATH TEST")
    print("=" * 70)

    print(
        "\nThis test uses simulated evidence."
    )

    print(
        "No real Prometheus incident detection is performed."
    )

    print(
        "Kubernetes remediation should remain in DRY_RUN mode."
    )

    # ========================================================
    # BUILD WORKFLOW
    # ========================================================

    workflow = build_incident_test_workflow()

    print(
        "\nComplete incident test workflow created successfully."
    )

    # ========================================================
    # SIMULATED CRITICAL INCIDENT
    # ========================================================

    test_state = {

        "messages": [],

        "incident_detected": True,

        "incidents": [

            {
                "type": "CPU",

                "pod": "payment-service-test",

                "severity": "CRITICAL",

                "value": 0.95,

                "message": (
                    "payment-service-test CPU usage "
                    "is critically high"
                )
            }
        ],

        "severity": "CRITICAL",

        # ----------------------------------------------------
        # Simulated remediation information
        #
        # The remediation agent can use the incident itself
        # to determine the affected deployment.
        # ----------------------------------------------------

        "remediation_attempt": 0
    }

    # ========================================================
    # START WORKFLOW
    # ========================================================

    print(
        "\nStarting complete simulated incident path..."
    )

    print(
        "-" * 70
    )

    try:

        final_state = workflow.invoke(
            test_state
        )

    except Exception as error:

        print(
            "\nWORKFLOW FAILED"
        )

        print(
            f"Error: {error}"
        )

        raise

    print(
        "-" * 70
    )

    print(
        "\nCOMPLETE INCIDENT PATH FINISHED"
    )

    # ========================================================
    # DISPLAY RESULTS
    # ========================================================

    display_results(
        final_state
    )

    print(
        "\n" + "=" * 70
    )

    print(
        "       END-TO-END INCIDENT TEST COMPLETED"
    )

    print(
        "=" * 70
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()