import sys

sys.path.insert(
    0,
    "agents/incident-analysis-agent/agents"
)

from evidence import evidence_agent

state = {
    "incidents": [],
    "incident_detected": False
}

result = evidence_agent(state)

print("\n===== EVIDENCE RESULT =====")
print(result)
