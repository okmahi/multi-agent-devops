import sys

# Add incident-analysis agents directory
sys.path.insert(
    0,
    "agents/incident-analysis-agent/agents"
)

from incident_detection import incident_detection_agent
from evidence import evidence_agent


# ============================================================
# Initial State
# ============================================================

state = {
    "incidents": [],
    "incident_detected": False,
    "messages": []
}


# ============================================================
# STEP 1 — Incident Detection
# ============================================================

print("\n" + "=" * 70)
print("STEP 1: INCIDENT DETECTION")
print("=" * 70)

state = incident_detection_agent(state)

print("\nIncident detected:")
print(state["incident_detected"])

print("\nIncidents:")
for incident in state["incidents"]:
    print(incident)


# ============================================================
# STEP 2 — Evidence Collection
# ============================================================

print("\n" + "=" * 70)
print("STEP 2: EVIDENCE COLLECTION")
print("=" * 70)

state = evidence_agent(state)


# ============================================================
# STEP 3 — Display Evidence
# ============================================================

print("\n" + "=" * 70)
print("STEP 3: EVIDENCE RESULT")
print("=" * 70)

evidence = state.get("evidence", {})

print("\nServices:")
print(evidence.get("services"))

print("\nCPU:")
print(evidence.get("cpu"))

print("\nMemory:")
print(evidence.get("memory"))

print("\nPods:")
print(evidence.get("pods"))

print("\nEvidence collected:")
print(state.get("evidence_collected"))

print("\nIncident detected:")
print(state.get("incident_detected"))

print("\nMessages:")
print(state.get("messages"))
