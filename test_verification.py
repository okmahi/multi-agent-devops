import sys

sys.path.insert(

    0,

    "agents/incident-analysis-agent"

)

from graph.workflow import build_workflow

print("\n" + "=" * 70)
print("        MULTI-AGENT DEVOPS INCIDENT WORKFLOW")
print("=" * 70)

print("\nStarting LangGraph workflow...")

# ============================================================
# INITIAL STATE
# ============================================================

initial_state = {
    "messages": [],
    "incidents": [],
    "incident_detected": False,
}

# ============================================================
# BUILD WORKFLOW
# ============================================================

workflow = build_workflow()

print("\nWorkflow compiled successfully.")

# ============================================================
# EXECUTE WORKFLOW
# ============================================================

try:

    final_state = workflow.invoke(
        initial_state
    )

except Exception as error:

    print("\n" + "=" * 70)
    print("WORKFLOW FAILED")
    print("=" * 70)

    print(f"\nError: {error}")

    raise

# ============================================================
# FINAL RESULT
# ============================================================

print("\n" + "=" * 70)
print("        WORKFLOW COMPLETED")
print("=" * 70)

incident_detected = final_state.get(
    "incident_detected",
    False
)

incidents = final_state.get(
    "incidents",
    []
)

print("\nIncident Detected:")
print(incident_detected)

print("\nIncident Count:")
print(len(incidents))

if final_state.get("diagnosis"):

    print("\nDiagnosis:")
    print(final_state.get("diagnosis"))

if final_state.get("recommendation"):

    print("\nRecommendation:")
    print(final_state.get("recommendation"))

if final_state.get("ai_analysis"):

    print("\nAI Analysis:")
    print(final_state.get("ai_analysis"))

remediation = final_state.get(
    "remediation"
)

if remediation:

    print("\nRemediation:")
    print(remediation)

verification = final_state.get(
    "verification"
)

if verification:

    print("\nVerification:")
    print(
        f"Status: {verification.get('status')}"
    )

    print(
        f"Result: {verification.get('result')}"
    )

    print(
        f"Confidence: {verification.get('confidence')}"
    )

    findings = verification.get(
        "findings",
        []
    )

    if findings:

        print("\nVerification Evidence:")

        for finding in findings:

            print(f"- {finding}")

messages = final_state.get(
    "messages",
    []
)

print("\nMessages:")

for message in messages:

    print(f"- {message}")

print("\n" + "=" * 70)
