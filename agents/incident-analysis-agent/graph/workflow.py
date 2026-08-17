from typing import TypedDict, Dict, Any, List, Optional

from langgraph.graph import StateGraph, END

from agents.monitoring import monitoring_agent
from agents.incident_detection import (
    incident_detection_agent
)
from agents.evidence import evidence_agent
from agents.diagnosis import diagnosis_agent
from agents.recommendation import recommendation_agent
from agents.ai_analysis import ai_analysis_agent
from agents.remediation import remediation_agent
from agents.verification import verification_agent


# ============================================================
# DEVOPS WORKFLOW STATE
# ============================================================

class DevOpsState(
    TypedDict,
    total=False
):

    # --------------------------------------------------------
    # Monitoring
    # --------------------------------------------------------

    monitoring_completed: bool

    monitoring_data: Dict[str, Any]

    # --------------------------------------------------------
    # Incident Detection
    # --------------------------------------------------------

    incident_detected: bool

    incidents: List[
        Dict[str, Any]
    ]

    incident_type: Optional[str]

    severity: Optional[str]

    # --------------------------------------------------------
    # Evidence
    # --------------------------------------------------------

    evidence_collected: bool

    evidence: Dict[str, Any]

    kubernetes_evidence: List[Any]

    prometheus_evidence: List[Any]

    log_evidence: List[Any]

    # --------------------------------------------------------
    # Diagnosis
    # --------------------------------------------------------

    diagnosis: Optional[str]

    root_cause: Optional[str]

    diagnostic_evidence: Dict[str, Any]

    # --------------------------------------------------------
    # Recommendation
    # --------------------------------------------------------

    recommendation: Optional[str]

    # --------------------------------------------------------
    # AI Analysis
    # --------------------------------------------------------

    ai_analysis: Optional[str]

    # --------------------------------------------------------
    # Remediation
    #
    # IMPORTANT:
    # The complete remediation result is stored in:
    #
    #     state["remediation"]
    #
    # Verification reads the same structure.
    # --------------------------------------------------------

    remediation: Dict[str, Any]

    remediation_attempt: int

    # --------------------------------------------------------
    # Verification
    # --------------------------------------------------------

    verification: Dict[str, Any]

    verification_status: Optional[str]

    verification_result: Optional[str]

    verification_confidence: Optional[str]

    verification_findings: List[str]

    # --------------------------------------------------------
    # Workflow Messages
    # --------------------------------------------------------

    messages: List[str]


# ============================================================
# ROUTE AFTER INCIDENT DETECTION
# ============================================================

def route_after_detection(
    state: DevOpsState
):

    incident_detected = state.get(
        "incident_detected",
        False
    )

    incidents = state.get(
        "incidents",
        []
    )

    if (
        incident_detected
        and incidents
    ):

        print(
            "\n[Workflow Router]"
        )

        print(
            f"Incident detected: "
            f"{len(incidents)} incident(s)."
        )

        print(
            "Starting evidence collection."
        )

        return "evidence"

    print(
        "\n[Workflow Router]"
    )

    print(
        "No incident detected."
    )

    print(
        "Workflow completed."
    )

    return "end"


# ============================================================
# ROUTE AFTER VERIFICATION
# ============================================================

def route_after_verification(
    state: DevOpsState
):

    status = state.get(
        "verification_status",
        "UNKNOWN"
    )

    attempt = state.get(
        "remediation_attempt",
        0
    )

    # ========================================================
    # RECOVERY CONFIRMED
    # ========================================================

    if status == "RECOVERED":

        print(
            "\n[Workflow Router]"
        )

        print(
            "Incident recovery confirmed."
        )

        print(
            "Workflow completed successfully."
        )

        return "end"

    # ========================================================
    # RECOVERY NOT CONFIRMED
    #
    # Retry only when remediation was actually attempted.
    #
    # Maximum two remediation attempts.
    # ========================================================

    if status in [
        "NOT_RECOVERED",
        "RECOVERY_PENDING"
    ]:

        if attempt < 2:

            print(
                "\n[Workflow Router]"
            )

            print(
                "Incident condition "
                "has not recovered."
            )

            print(
                f"Starting remediation "
                f"attempt {attempt + 1}."
            )

            return "remediation"

        print(
            "\n[Workflow Router]"
        )

        print(
            "Maximum automated remediation "
            "attempts reached."
        )

        print(
            "Manual investigation is required."
        )

        return "end"

    # ========================================================
    # NOT VERIFIED
    #
    # This normally occurs when:
    #
    #     DRY_RUN=True
    #
    # or remediation was not executed.
    #
    # Do NOT automatically retry.
    # ========================================================

    if status == "NOT_VERIFIED":

        print(
            "\n[Workflow Router]"
        )

        print(
            "Recovery could not be verified."
        )

        print(
            "No additional automatic remediation "
            "will be triggered."
        )

        print(
            "Manual verification is required."
        )

        return "end"

    # ========================================================
    # UNKNOWN STATUS
    # ========================================================

    print(
        "\n[Workflow Router]"
    )

    print(
        f"Unknown verification status: "
        f"{status}"
    )

    print(
        "Stopping automated workflow."
    )

    return "end"


# ============================================================
# BUILD WORKFLOW
# ============================================================

def build_workflow():

    workflow = StateGraph(
        DevOpsState
    )

    # ========================================================
    # REGISTER AGENTS
    # ========================================================

    workflow.add_node(
        "monitoring",
        monitoring_agent
    )

    workflow.add_node(
        "incident_detection",
        incident_detection_agent
    )

    workflow.add_node(
        "evidence",
        evidence_agent
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
    # ENTRY POINT
    # ========================================================

    workflow.set_entry_point(
        "monitoring"
    )

    # ========================================================
    # MONITORING
    # ========================================================

    workflow.add_edge(
        "monitoring",
        "incident_detection"
    )

    # ========================================================
    # INCIDENT DETECTION
    # ========================================================

    workflow.add_conditional_edges(

        "incident_detection",

        route_after_detection,

        {
            "evidence": "evidence",
            "end": END
        }

    )

    # ========================================================
    # EVIDENCE
    # ========================================================

    workflow.add_edge(
        "evidence",
        "diagnosis"
    )

    # ========================================================
    # DIAGNOSIS
    # ========================================================

    workflow.add_edge(
        "diagnosis",
        "recommendation"
    )

    # ========================================================
    # RECOMMENDATION
    # ========================================================

    workflow.add_edge(
        "recommendation",
        "ai_analysis"
    )

    # ========================================================
    # AI ANALYSIS
    # ========================================================

    workflow.add_edge(
        "ai_analysis",
        "remediation"
    )

    # ========================================================
    # REMEDIATION
    # ========================================================

    workflow.add_edge(
        "remediation",
        "verification"
    )

    # ========================================================
    # VERIFICATION
    # ========================================================

    workflow.add_conditional_edges(

        "verification",

        route_after_verification,

        {
            "remediation": "remediation",
            "end": END
        }

    )

    # ========================================================
    # COMPILE
    # ========================================================

    return workflow.compile()