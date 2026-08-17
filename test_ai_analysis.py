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


state = {
    "incidents": [],
    "incident_detected": False,
    "messages": []
}


print("\n" + "=" * 70)
print("STEP 1: INCIDENT DETECTION")
print("=" * 70)

state = incident_detection_agent(state)


print("\n" + "=" * 70)
print("STEP 2: EVIDENCE COLLECTION")
print("=" * 70)

state = evidence_agent(state)


print("\n" + "=" * 70)
print("STEP 3: DIAGNOSIS")
print("=" * 70)

state = diagnosis_agent(state)


print("\n" + "=" * 70)
print("STEP 4: RECOMMENDATION")
print("=" * 70)

state = recommendation_agent(state)


print("\n" + "=" * 70)
print("STEP 5: AI ANALYSIS")
print("=" * 70)

state = ai_analysis_agent(state)


print("\n" + "=" * 70)
print("AI ANALYSIS RESULT")
print("=" * 70)

print(state.get("ai_analysis"))

print("\nMessages:")
print(state.get("messages"))
