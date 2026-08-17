import sys

sys.path.insert(
    0,
    "agents/incident-analysis-agent/agents"
)

from incident_detection import incident_detection_agent
from evidence import evidence_agent
from diagnosis import diagnosis_agent
from recommendation import recommendation_agent
from remediation import remediation_agent


state = {
    "incidents": [],
    "incident_detected": False,
    "messages": []
}


print("=" * 70)
print("STEP 1: INCIDENT DETECTION")
print("=" * 70)

state = incident_detection_agent(state)

print("\nIncident detected:")
print(state["incident_detected"])

print("\nIncidents:")
for incident in state["incidents"]:
    print(incident)


print("\n" + "=" * 70)
print("STEP 2: EVIDENCE COLLECTION")
print("=" * 70)

state = evidence_agent(state)

print("\nEvidence collected:")
print(state.get("evidence_collected"))


print("\n" + "=" * 70)
print("STEP 3: DIAGNOSIS")
print("=" * 70)

state = diagnosis_agent(state)

print("\nSeverity:")
print(state.get("severity"))

print("\nDiagnosis:")
print(state.get("diagnosis"))

print("\nRoot Cause:")
print(state.get("root_cause"))


print("\n" + "=" * 70)
print("STEP 4: RECOMMENDATION")
print("=" * 70)

state = recommendation_agent(state)

print("\nRecommendation:")
print(state.get("recommendation"))


print("\n" + "=" * 70)
print("STEP 5: REMEDIATION")
print("=" * 70)

state = remediation_agent(state)

print("\n" + "=" * 70)
print("REMEDIATION RESULT")
print("=" * 70)

print("Mode:")
print(state["remediation"]["mode"])

print("\nAction:")
print(state["remediation"]["action"])

print("\nTarget Pod:")
print(state["remediation"]["target_pod"])

print("\nTarget Service:")
print(state["remediation"]["target_service"])

print("\nExecuted:")
print(state["remediation"]["executed"])

print("\nStatus:")
print(state["remediation"]["status"])

print("\nReason:")
print(state["remediation"]["reason"])

print("\nMessages:")
print(state["messages"])
