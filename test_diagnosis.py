import sys

# Add incident-analysis agents directory
sys.path.insert(
    0,
    "agents/incident-analysis-agent/agents"
)

from incident_detection import incident_detection_agent
from evidence import evidence_agent
from diagnosis import diagnosis_agent


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

print("\nIncident detected:", state.get("incident_detected"))

print("\nDetected incidents:")
for incident in state.get("incidents", []):
    print(incident)


# ============================================================
# STEP 2 — Evidence Collection
# ============================================================

print("\n" + "=" * 70)
print("STEP 2: EVIDENCE COLLECTION")
print("=" * 70)

state = evidence_agent(state)

print("\nEvidence collected:", state.get("evidence_collected"))


# ============================================================
# STEP 3 — Diagnosis
# ============================================================

print("\n" + "=" * 70)
print("STEP 3: DIAGNOSIS / ROOT CAUSE ANALYSIS")
print("=" * 70)

state = diagnosis_agent(state)


# ============================================================
# STEP 4 — Diagnosis Result
# ============================================================

print("\n" + "=" * 70)
print("DIAGNOSIS RESULT")
print("=" * 70)

print("\nSeverity:")
print(state.get("severity"))

print("\nDiagnosis:")
print(state.get("diagnosis"))

print("\nRoot Cause:")
print(state.get("root_cause"))

print("\nDiagnostic Evidence:")
print(state.get("diagnostic_evidence"))

print("\nMessages:")
print(state.get("messages"))
