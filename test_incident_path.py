import sys
import os

print("Current directory:", os.getcwd())
print("Python path:", sys.path)
print("Agents directory exists:", os.path.exists('agents'))
print("__init__.py exists:", os.path.exists('agents/__init__.py'))
print("monitoring_agent.py exists:", os.path.exists('agents/monitoring_agent.py'))

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import logging
from agents.monitoring_agent import monitoring_agent
from agents.incident_detection import incident_detection_agent
from agents.evidence_agent import evidence_agent
from agents.diagnosis_agent import diagnosis_agent
from agents.recommendation_agent import recommendation_agent
from agents.ai_analysis_agent import ai_analysis_agent
from agents.remediation import remediation_agent
from agents.verification_agent import verification_agent

logging.basicConfig(
    level=logging.INFO,
    format='[%(name)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# TEST: SIMULATED INCIDENT PATH
# ============================================================================

def test_incident_path():
    """
    Test the full incident response workflow with simulated critical CPU incident.
    
    This test simulates a real incident scenario:
    1. Monitoring detects critical CPU usage
    2. Incident Detection generates incident
    3. Evidence collection
    4. Diagnosis analysis
    5. Recommendation generation
    6. AI analysis
    7. Remediation (rollout restart)
    8. Verification
    """
    
    print("\n" + "="*70)
    print("       SIMULATED INCIDENT PATH TEST")
    print("="*70)
    
    # ========================================================================
    # INITIAL STATE: Simulate monitoring data with critical CPU incident
    # ========================================================================
    
    state = {
        "monitoring_data": {
            "services": ["payment-service", "inventory-service", "user-service"],
            "cpu": {
                # CRITICAL: payment-service pod with 1.2 cores (threshold: 1.5)
                # Actually, let's make it actually critical
                "payment-service-77dfdb4b86-bbp65": 1.6,  # CRITICAL (> 1.5)
                "inventory-service-6f958cfc58-5652l": 0.003,
                "user-service-689c8f89d5-5xg58": 0.003,
                "payment-service-77dfdb4b86-x45vk": 0.003,
                "payment-service-77dfdb4b86-66zfs": 0.003,
            },
            "memory": {
                "inventory-service-6f958cfc58-5652l": 83.73,
                "payment-service-77dfdb4b86-bbp65": 50.66,
                "user-service-689c8f89d5-5xg58": 68.00,
            },
            "availability": {
                "payment-service": 1.0,
                "inventory-service": 1.0,
                "user-service": 1.0,
            }
        },
        "incidents": [],
        "messages": []
    }
    
    # ========================================================================
    # STEP 1: EVIDENCE
    # ========================================================================
    
    print("\n" + "="*70)
    print("STEP 1: EVIDENCE")
    print("="*70)
    
    state = evidence_agent(state)
    print(f"\n[Evidence Agent]")
    print(f"Collecting incident evidence...")
    print(f"Evidence collection completed.\n")
    
    # ========================================================================
    # STEP 2: INCIDENT DETECTION (using monitoring data)
    # ========================================================================
    
    print("="*70)
    print("STEP 2: INCIDENT DETECTION")
    print("="*70)
    
    state = incident_detection_agent(state)
    print(f"\n[Incident Detection Agent]")
    print(f"Monitoring data: {list(state['monitoring_data'].keys())}")
    print(f"Incidents detected: {len(state['incidents'])}")
    for inc in state['incidents']:
        print(f"  - {inc['type']}: {inc['pod']} = {inc['value']} (severity: {inc['severity']})")
    print()
    
    # ========================================================================
    # STEP 3: DIAGNOSIS
    # ========================================================================
    
    print("="*70)
    print("STEP 3: DIAGNOSIS")
    print("="*70)
    
    state = diagnosis_agent(state)
    print(f"\n[Diagnosis Agent]")
    print(f"Analysing incident evidence...\n")
    
    if state.get("diagnosis"):
        diag = state["diagnosis"]
        print(f"Severity: {diag.get('severity')}\n")
        print(f"Confirmed Findings:")
        for finding in diag.get("confirmed_findings", []):
            print(f"- {finding}")
        print(f"\nSupporting Evidence:")
        for evidence in diag.get("supporting_evidence", []):
            print(f"- {evidence}")
        print(f"\nPossible Causes:")
        for cause in diag.get("possible_causes", []):
            print(f"- {cause}")
        print(f"\nRoot Cause Confidence: {diag.get('root_cause_confidence')}\n")
    
    # ========================================================================
    # STEP 4: RECOMMENDATION
    # ========================================================================
    
    print("="*70)
    print("STEP 4: RECOMMENDATION")
    print("="*70)
    
    state = recommendation_agent(state)
    print(f"\n[Recommendation Agent]")
    print(f"Generating recommended action...\n")
    
    if state.get("recommendation"):
        rec = state["recommendation"]
        print(f"Severity:\n{rec.get('severity')}\n")
        print(f"Recommended Action:")
        for i, action in enumerate(rec.get("actions", []), 1):
            print(f"{i}. {action}")
        print()
    
    # ========================================================================
    # STEP 5: AI ANALYSIS
    # ========================================================================
    
    print("="*70)
    print("STEP 5: AI ANALYSIS")
    print("="*70)
    
    state = ai_analysis_agent(state)
    print(f"\n[AI Analysis Agent]")
    print(f"Sending incident data to OpenRouter...\n")
    
    if state.get("ai_analysis"):
        ai_analysis = state["ai_analysis"]
        # Print each section of the report
        for section in ["summary", "root_cause", "evidence", "impact", "action", "confidence"]:
            if section in ai_analysis:
                print(f"{section.upper()}")
                print(f"{ai_analysis[section]}\n")
    else:
        # Fallback analysis
        print("Deterministic fallback analysis:")
        if state.get("ai_analysis_fallback"):
            for section in ["summary", "root_cause", "evidence", "impact", "action", "confidence"]:
                if section in state["ai_analysis_fallback"]:
                    print(f"{section.upper()}")
                    print(f"{state['ai_analysis_fallback'][section]}\n")
    
    # ========================================================================
    # STEP 6: REMEDIATION
    # ========================================================================
    
    print("="*70)
    print("STEP 6: REMEDIATION")
    print("="*70)
    
    state = remediation_agent(state)
    print(f"\n[Remediation Agent]\n")
    
    if state.get("remediation_results"):
        rem = state["remediation_results"]
        print(f"Status: {rem.get('status')}")
        print(f"Message: {rem.get('message')}\n")
        
        for result in rem.get("results", []):
            print(f"  Incident Type: {result.get('incident_type')}")
            print(f"  Original Pod: {result.get('original_pod')}")
            print(f"  Deployment: {result.get('deployment', 'N/A')}")
            print(f"  Status: {result.get('status')}")
            print(f"  Message: {result.get('message')}\n")
    
    # ========================================================================
    # STEP 7: VERIFICATION
    # ========================================================================
    
    print("="*70)
    print("STEP 7: VERIFICATION")
    print("="*70)
    
    state = verification_agent(state)
    print(f"\n[Verification Agent]")
    print(f"Verifying incident recovery...\n")
    
    if state.get("verification"):
        verif = state["verification"]
        print(f"Verification Status: {verif.get('status')}")
        print(f"Verification Result: {verif.get('result')}")
        print(f"Confidence: {verif.get('confidence')}\n")
    
    # ========================================================================
    # FINAL SUMMARY
    # ========================================================================
    
    print("="*70)
    print("       SIMULATED INCIDENT TEST COMPLETED")
    print("="*70)
    
    print(f"\nIncident: {json.dumps(state.get('incidents', []), indent=2)}")
    print(f"\nDiagnosis: {state.get('diagnosis', {}).get('summary', 'N/A')}")
    print(f"\nRecommendation: {state.get('recommendation', {}).get('summary', 'N/A')}")
    print(f"\nAI Analysis: {state.get('ai_analysis', state.get('ai_analysis_fallback', {}))}")
    print(f"\nRemediation: {state.get('remediation_results', {})}")
    print(f"\nVerification: {state.get('verification', {})}")
    print(f"\nMessages: {state.get('messages', [])}")
    print()

if __name__ == "__main__":
    test_incident_path()
