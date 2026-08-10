import os

from dotenv import load_dotenv
from openai import OpenAI


# ============================================================
# Configuration
# ============================================================

load_dotenv()

OPENROUTER_API_KEY = os.getenv(
    "OPENROUTER_API_KEY"
)

if not OPENROUTER_API_KEY:
    raise RuntimeError(
        "OPENROUTER_API_KEY is not configured."
    )


# ============================================================
# OpenRouter Client
# ============================================================

client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)


# ============================================================
# AI Incident Analysis
# ============================================================

def analyse_incident(rca_data):

    prompt = f"""
You are an AI DevOps incident analysis agent.

Analyse the following deterministic RCA result from a
Kubernetes monitoring system.

RCA DATA:

Severity:
{rca_data["severity"]}

Root Cause:
{rca_data["root_cause"]}

Evidence:
{rca_data["evidence"]}

Recommended Action:
{rca_data["recommendation"]}

Provide a concise incident analysis using this structure:

1. Incident Summary
2. Likely Root Cause
3. Evidence
4. Impact
5. Recommended Action
6. Confidence

Important rules:

- Do not invent evidence.
- Use only the supplied RCA evidence.
- Clearly distinguish confirmed evidence from inference.
- Keep the analysis suitable for a DevOps engineer.
"""

    response = client.chat.completions.create(
        model="openrouter/free",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response.choices[0].message.content


# ============================================================
# Main
# ============================================================

def main():

    print("=" * 60)
    print("          AI INCIDENT ANALYSIS AGENT")
    print("=" * 60)

    # --------------------------------------------------------
    # Test RCA data
    # --------------------------------------------------------

    rca_data = {

        "severity": "CRITICAL",

        "root_cause": (
            "payment-service has no running pod."
        ),

        "evidence": (
            "Prometheus reports the payment-service "
            "as DOWN and no corresponding Kubernetes "
            "pod was found."
        ),

        "recommendation": (
            "Check the payment-service deployment, "
            "replica count, EndpointSlice and "
            "Kubernetes events."
        )
    }

    print("\nSending RCA evidence to OpenRouter...")

    try:

        analysis = analyse_incident(
            rca_data
        )

        print("\n" + "-" * 60)
        print("AI INCIDENT ANALYSIS")
        print("-" * 60)

        print()
        print(analysis)

    except Exception as error:

        print("\nAI analysis failed:")
        print(error)

    print("\n" + "=" * 60)
    print("       AI ANALYSIS COMPLETED")
    print("=" * 60)


# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":
    main()