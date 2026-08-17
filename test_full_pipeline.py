import sys

sys.path.insert(
    0,
    "agents/incident-analysis-agent/agents"
)

from incident_detection import incident_detection_agent
from evidence import evidence_agent
from diagnosis import diagnosis_agent
from recommendation import recommendation_agent
from ai_analysis import ai_analysis_agent
from remediation import remediation_agent
from verification import verification_agent


state = {
    "incidents": [],
    "incident_detected": False,
    "messages": []
}


print("=" * 70)
print("MULTI-AGENT DEVOPS INCIDENT ANALYSIS")
print("=" * 70)


print("\n[1] INCIDENT DETECTION")
state = incident_detection_agent(state)


print("\n[2] EVIDENCE COLLECTION")
state = evidence_agent(state)


print("\n[3] DIAGNOSIS / RCA")
state = diagnosis_agent(state)


print("\n[4] RECOMMENDATION")
state = recommendation_agent(state)


print("\n[5] AI ANALYSIS")
state = ai_analysis_agent(state)


print("\n[6] REMEDIATION")
state = remediation_agent(state)


print("\n[7] VERIFICATION")
state = verification_agent(state)


print("\n" + "=" * 70)
print("FINAL PIPELINE RESULT")
print("=" * 70)

print("\nIncident Detected:")
print(state.get("incident_detected"))

print("\nSeverity:")
print(state.get("severity"))

print("\nRoot Cause:")
print(state.get("root_cause"))

print("\nRecommendation:")
print(state.get("recommendation"))

print("\nAI Analysis:")
print(state.get("ai_analysis"))

print("\nRemediation:")
print(state.get("remediation"))

print("\nVerification:")
print(state.get("verification"))

print("\nMessages:")
print(state.get("messages"))
