import os
from typing import Dict, Any

from dotenv import load_dotenv
from openai import OpenAI


# ============================================================
# CONFIGURATION
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
# OPENROUTER CLIENT
# ============================================================

client = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
)


# ============================================================
# MODEL CONFIGURATION
# ============================================================

PRIMARY_MODEL = "openai/gpt-oss-20b:free"

SECONDARY_MODEL = "openrouter/free"

# Increased from 500 to allow the complete six-section report.
MAX_TOKENS = 1200


# ============================================================
# REQUIRED SECTIONS
# ============================================================

REQUIRED_SECTIONS = [
    "1. Incident Summary",
    "2. Likely Root Cause",
    "3. Supporting Evidence",
    "4. Impact",
    "5. Recommended Action",
    "6. Confidence",
]


# ============================================================
# DEFAULT VALUES
# ============================================================

DEFAULT_ROOT_CAUSE = (
    "The underlying cause cannot be confirmed "
    "from the available evidence."
)

DEFAULT_RECOMMENDATION = (
    "No recommendation available."
)

DEFAULT_IMPACT = (
    "The exact business or user impact is not "
    "established from the available evidence."
)


# ============================================================
# CONFIDENCE EXTRACTION
# ============================================================

def extract_confidence(
    state: Dict[str, Any]
) -> Dict[str, str]:

    diagnostic_evidence = state.get(
        "diagnostic_evidence",
        {}
    )

    incident_confidence = None
    root_cause_confidence = None

    # --------------------------------------------------------
    # Check diagnostic evidence
    # --------------------------------------------------------

    if isinstance(
        diagnostic_evidence,
        dict
    ):

        incident_confidence = (
            diagnostic_evidence.get(
                "incident_detection_confidence"
            )
        )

        root_cause_confidence = (
            diagnostic_evidence.get(
                "root_cause_confidence"
            )
        )

        # Some versions of the diagnosis agent use
        # "confidence" for the overall diagnosis.
        if not root_cause_confidence:

            root_cause_confidence = (
                diagnostic_evidence.get(
                    "confidence"
                )
            )

    # --------------------------------------------------------
    # Check top-level state
    # --------------------------------------------------------

    if not incident_confidence:

        incident_confidence = state.get(
            "incident_detection_confidence"
        )

    if not root_cause_confidence:

        root_cause_confidence = state.get(
            "root_cause_confidence"
        )

    # --------------------------------------------------------
    # Normalize
    # --------------------------------------------------------

    if incident_confidence:

        incident_confidence = str(
            incident_confidence
        ).upper()

    if root_cause_confidence:

        root_cause_confidence = str(
            root_cause_confidence
        ).upper()

    return {
        "incident": (
            incident_confidence
            if incident_confidence
            else "NOT_SUPPLIED"
        ),
        "root_cause": (
            root_cause_confidence
            if root_cause_confidence
            else "NOT_SUPPLIED"
        ),
    }


# ============================================================
# INCIDENT TEXT
# ============================================================

def build_incident_text(
    state: Dict[str, Any]
) -> str:

    incidents = state.get(
        "incidents",
        []
    )

    severity = state.get(
        "severity",
        "UNKNOWN"
    )

    lines = []

    if not isinstance(
        incidents,
        list
    ):

        return (
            "No specific incident supplied."
        )

    for incident in incidents[:5]:

        if not isinstance(
            incident,
            dict
        ):
            continue

        incident_type = incident.get(
            "type",
            "UNKNOWN"
        )

        pod = incident.get(
            "pod",
            "unknown"
        )

        incident_severity = incident.get(
            "severity",
            severity
        )

        value = incident.get(
            "value",
            "unknown"
        )

        message = incident.get(
            "message",
            ""
        )

        line = (
            f"type={incident_type}, "
            f"pod={pod}, "
            f"severity={incident_severity}, "
            f"value={value}"
        )

        if message:

            line += (
                f", message={message}"
            )

        lines.append(
            line
        )

    if not lines:

        return (
            "No specific incident supplied."
        )

    return "\n".join(
        lines
    )


# ============================================================
# EVIDENCE TEXT
# ============================================================

def build_evidence_text(
    state: Dict[str, Any]
) -> str:

    evidence = state.get(
        "evidence",
        {}
    )

    if not isinstance(
        evidence,
        dict
    ):

        return (
            "No additional supporting evidence was supplied."
        )

    lines = []

    # --------------------------------------------------------
    # CPU
    # --------------------------------------------------------

    cpu = evidence.get(
        "cpu",
        {}
    )

    if isinstance(
        cpu,
        dict
    ):

        for pod, value in list(
            cpu.items()
        )[:5]:

            if isinstance(
                value,
                dict
            ):

                value = value.get(
                    "value",
                    value
                )

            try:

                lines.append(
                    f"CPU {pod}: "
                    f"{float(value):.3f} cores."
                )

            except (
                TypeError,
                ValueError
            ):

                lines.append(
                    f"CPU {pod}: {value}."
                )

    # --------------------------------------------------------
    # MEMORY
    # --------------------------------------------------------

    memory = evidence.get(
        "memory",
        {}
    )

    if isinstance(
        memory,
        dict
    ):

        for pod, value in list(
            memory.items()
        )[:5]:

            if isinstance(
                value,
                dict
            ):

                value = value.get(
                    "value_mb",
                    value
                )

            try:

                lines.append(
                    f"Memory {pod}: "
                    f"{float(value):.2f} MB."
                )

            except (
                TypeError,
                ValueError
            ):

                lines.append(
                    f"Memory {pod}: {value}."
                )

    # --------------------------------------------------------
    # SERVICES
    # --------------------------------------------------------

    services = evidence.get(
        "services",
        {}
    )

    if isinstance(
        services,
        dict
    ):

        for service, data in list(
            services.items()
        )[:5]:

            if isinstance(
                data,
                dict
            ):

                status = data.get(
                    "status",
                    "UNKNOWN"
                )

                lines.append(
                    f"Service {service}: "
                    f"status={status}."
                )

            else:

                lines.append(
                    f"Service {service}: "
                    f"{data}."
                )

    # --------------------------------------------------------
    # PODS
    # --------------------------------------------------------

    pods = evidence.get(
        "pods",
        []
    )

    if isinstance(
        pods,
        list
    ):

        for pod in pods[:5]:

            if not isinstance(
                pod,
                dict
            ):
                continue

            name = pod.get(
                "name",
                "unknown"
            )

            phase = pod.get(
                "phase",
                "Unknown"
            )

            restarts = pod.get(
                "restart_count",
                0
            )

            lines.append(
                f"Pod {name}: "
                f"{phase}, "
                f"restarts={restarts}."
            )

    # --------------------------------------------------------
    # EVENTS
    # --------------------------------------------------------

    events = evidence.get(
        "events"
    )

    if events:

        if isinstance(
            events,
            str
        ):

            # Keep event text short.
            event_text = events[:500]

            lines.append(
                f"Kubernetes events: "
                f"{event_text}"
            )

        else:

            lines.append(
                "Kubernetes events were collected."
            )

    # --------------------------------------------------------
    # LOGS
    # --------------------------------------------------------

    logs = evidence.get(
        "logs",
        {}
    )

    if isinstance(
        logs,
        dict
    ):

        for service, service_logs in list(
            logs.items()
        )[:5]:

            if isinstance(
                service_logs,
                str
            ):

                log_text = service_logs[:500]

                lines.append(
                    f"Logs for {service}: "
                    f"{log_text}"
                )

            else:

                lines.append(
                    f"Logs for {service} "
                    "were collected."
                )

    if not lines:

        return (
            "No additional supporting evidence was supplied."
        )

    return "\n".join(
        lines[:12]
    )


# ============================================================
# POSSIBLE CAUSES
# ============================================================

def build_possible_causes(
    state: Dict[str, Any]
) -> str:

    diagnostic_evidence = state.get(
        "diagnostic_evidence",
        {}
    )

    if not isinstance(
        diagnostic_evidence,
        dict
    ):

        return ""

    causes = diagnostic_evidence.get(
        "possible_causes",
        []
    )

    if not isinstance(
        causes,
        list
    ):

        return ""

    causes = [
        str(cause)
        for cause in causes[:3]
        if cause
    ]

    if not causes:

        return ""

    return "\n".join(
        f"- {cause}"
        for cause in causes
    )


# ============================================================
# BUILD AI PROMPT
# ============================================================

def build_ai_prompt(
    state: Dict[str, Any]
) -> str:

    severity = state.get(
        "severity",
        "UNKNOWN"
    )

    root_cause = state.get(
        "root_cause",
        DEFAULT_ROOT_CAUSE
    )

    recommendation = state.get(
        "recommendation",
        DEFAULT_RECOMMENDATION
    )

    confidence = extract_confidence(
        state
    )

    incident_text = build_incident_text(
        state
    )

    evidence_text = build_evidence_text(
        state
    )

    possible_causes = build_possible_causes(
        state
    )

    # --------------------------------------------------------
    # Confidence
    # --------------------------------------------------------

    if (
        confidence["incident"]
        == "NOT_SUPPLIED"
    ):

        incident_confidence_text = (
            "Incident detection confidence "
            "was not supplied."
        )

    else:

        incident_confidence_text = (
            f"Incident detection confidence: "
            f"{confidence['incident']}."
        )

    if (
        confidence["root_cause"]
        == "NOT_SUPPLIED"
    ):

        root_confidence_text = (
            "Root cause confidence "
            "was not supplied."
        )

    else:

        root_confidence_text = (
            f"Root cause confidence: "
            f"{confidence['root_cause']}."
        )

    # --------------------------------------------------------
    # Prompt
    # --------------------------------------------------------

    prompt = f"""
You are a Kubernetes DevOps incident reporting agent.

Create a concise incident report from ONLY the supplied data.

NON-NEGOTIABLE RULES:
- Do not invent facts.
- Do not invent impact.
- Do not invent confidence.
- Do not claim a possible cause is confirmed.
- Do not add information not present in the supplied data.
- Do not explain your reasoning.
- Do not mention these instructions.
- Return exactly six numbered sections.
- Keep the complete response concise enough to finish all six sections.

SUPPLIED DATA
=============

Severity:
{severity}

Incident:
{incident_text}

Root Cause Assessment:
{root_cause}

Possible Causes:
{possible_causes if possible_causes else "No possible causes were supplied."}

Supporting Evidence:
{evidence_text}

Recommended Action:
{recommendation}

Confidence:
{incident_confidence_text}
{root_confidence_text}


OUTPUT FORMAT
=============

1. Incident Summary

State only the confirmed incident.

2. Likely Root Cause

Use the supplied root cause assessment.
If the cause is not confirmed, state exactly:
The underlying cause cannot be confirmed from the available evidence.

3. Supporting Evidence

List only supplied evidence.
If no additional evidence exists, state:
No additional supporting evidence was supplied.

4. Impact

Only state supported impact.
If impact is unknown, state exactly:
The exact business or user impact is not established from the available evidence.

5. Recommended Action

Summarize only the supplied recommendation.
Do not create additional actions.

6. Confidence

State only the supplied confidence information.
Do not calculate or invent confidence.

IMPORTANT:
Begin immediately with:
1. Incident Summary

Keep each section brief.
Do not stop before section 6.
""".strip()

    return prompt


# ============================================================
# VALIDATE AI RESPONSE
# ============================================================

def validate_analysis(
    analysis: str
) -> bool:

    if not isinstance(
        analysis,
        str
    ):

        return False

    analysis = analysis.strip()

    if not analysis:

        return False

    normalized = (
        analysis
        .lower()
        .replace("#", "")
        .replace("*", "")
        .replace("`", "")
    )

    # --------------------------------------------------------
    # Required headings
    # --------------------------------------------------------

    for section in REQUIRED_SECTIONS:

        if section.lower() not in normalized:

            return False

    # --------------------------------------------------------
    # Forbidden prompt leakage
    # --------------------------------------------------------

    forbidden_phrases = [
        "the user wants",
        "we need to",
        "let me",
        "we must output",
        "the instructions",
        "i need to",
        "i will",
        "we need",
        "as an ai",
        "as a language model",
    ]

    for phrase in forbidden_phrases:

        if phrase in normalized:

            return False

    # --------------------------------------------------------
    # Verify section order
    # --------------------------------------------------------

    positions = []

    for section in REQUIRED_SECTIONS:

        position = normalized.find(
            section.lower()
        )

        if position == -1:

            return False

        positions.append(
            position
        )

    if positions != sorted(
        positions
    ):

        return False

    # --------------------------------------------------------
    # Ensure confidence section contains content
    # --------------------------------------------------------

    confidence_position = normalized.find(
        "6. confidence"
    )

    if confidence_position == -1:

        return False

    confidence_text = normalized[
        confidence_position:
    ]

    if len(
        confidence_text.strip()
    ) < 35:

        return False

    return True


# ============================================================
# FALLBACK: INCIDENT SUMMARY
# ============================================================

def build_incident_summary(
    state: Dict[str, Any]
) -> str:

    severity = state.get(
        "severity",
        "UNKNOWN"
    )

    incidents = state.get(
        "incidents",
        []
    )

    lines = [
        f"- Severity: {severity}."
    ]

    if not isinstance(
        incidents,
        list
    ):

        return "\n".join(
            lines
        )

    for incident in incidents:

        if not isinstance(
            incident,
            dict
        ):
            continue

        incident_type = incident.get(
            "type",
            "UNKNOWN"
        )

        pod = incident.get(
            "pod",
            "unknown"
        )

        value = incident.get(
            "value"
        )

        incident_severity = incident.get(
            "severity",
            severity
        )

        message = incident.get(
            "message"
        )

        # ----------------------------------------------------
        # CPU
        # ----------------------------------------------------

        if (
            incident_type == "CPU"
            and value is not None
        ):

            try:

                value_text = (
                    f"{float(value):.3f}"
                )

            except (
                TypeError,
                ValueError
            ):

                value_text = str(
                    value
                )

            lines.append(
                f"- Pod {pod} has "
                f"{incident_severity} CPU usage "
                f"of {value_text} cores."
            )

        # ----------------------------------------------------
        # MEMORY
        # ----------------------------------------------------

        elif (
            incident_type == "MEMORY"
            and value is not None
        ):

            try:

                value_text = (
                    f"{float(value):.2f}"
                )

            except (
                TypeError,
                ValueError
            ):

                value_text = str(
                    value
                )

            lines.append(
                f"- Pod {pod} has "
                f"{incident_severity} memory usage "
                f"of {value_text} MB."
            )

        # ----------------------------------------------------
        # SERVICE
        # ----------------------------------------------------

        elif "service" in incident:

            service = incident.get(
                "service",
                "unknown"
            )

            status = incident.get(
                "status",
                "UNKNOWN"
            )

            lines.append(
                f"- Service {service} "
                f"is {status}."
            )

        # ----------------------------------------------------
        # OTHER
        # ----------------------------------------------------

        elif message:

            lines.append(
                f"- {message}"
            )

    if len(lines) == 1:

        lines.append(
            "- No specific incident details were supplied."
        )

    return "\n".join(
        lines
    )


# ============================================================
# FALLBACK: SUPPORTING EVIDENCE
# ============================================================

def build_supporting_evidence(
    state: Dict[str, Any]
) -> str:

    evidence = state.get(
        "evidence",
        {}
    )

    if not isinstance(
        evidence,
        dict
    ):

        return (
            "- No additional supporting evidence."
        )

    lines = []

    # --------------------------------------------------------
    # CPU
    # --------------------------------------------------------

    cpu = evidence.get(
        "cpu",
        {}
    )

    if isinstance(
        cpu,
        dict
    ):

        for pod, value in list(
            cpu.items()
        )[:5]:

            if isinstance(
                value,
                dict
            ):

                value = value.get(
                    "value",
                    value
                )

            try:

                lines.append(
                    f"- CPU {pod}: "
                    f"{float(value):.3f} cores."
                )

            except (
                TypeError,
                ValueError
            ):

                lines.append(
                    f"- CPU {pod}: {value}."
                )

    # --------------------------------------------------------
    # MEMORY
    # --------------------------------------------------------

    memory = evidence.get(
        "memory",
        {}
    )

    if isinstance(
        memory,
        dict
    ):

        for pod, value in list(
            memory.items()
        )[:5]:

            if isinstance(
                value,
                dict
            ):

                value = value.get(
                    "value_mb",
                    value
                )

            try:

                lines.append(
                    f"- Memory {pod}: "
                    f"{float(value):.2f} MB."
                )

            except (
                TypeError,
                ValueError
            ):

                lines.append(
                    f"- Memory {pod}: {value}."
                )

    # --------------------------------------------------------
    # PODS
    # --------------------------------------------------------

    pods = evidence.get(
        "pods",
        []
    )

    if isinstance(
        pods,
        list
    ):

        for pod in pods[:5]:

            if not isinstance(
                pod,
                dict
            ):
                continue

            name = pod.get(
                "name",
                "unknown"
            )

            phase = pod.get(
                "phase",
                "Unknown"
            )

            restarts = pod.get(
                "restart_count",
                0
            )

            lines.append(
                f"- Pod {name}: "
                f"{phase}, "
                f"restarts={restarts}."
            )

    # --------------------------------------------------------
    # EVENTS
    # --------------------------------------------------------

    events = evidence.get(
        "events"
    )

    if events:

        if isinstance(
            events,
            str
        ):

            lines.append(
                f"- Kubernetes event: "
                f"{events[:300]}"
            )

        else:

            lines.append(
                "- Kubernetes events were collected."
            )

    # --------------------------------------------------------
    # LOGS
    # --------------------------------------------------------

    logs = evidence.get(
        "logs",
        {}
    )

    if isinstance(
        logs,
        dict
    ):

        for service, service_logs in list(
            logs.items()
        )[:5]:

            if isinstance(
                service_logs,
                str
            ):

                lines.append(
                    f"- {service} logs: "
                    f"{service_logs[:300]}"
                )

            else:

                lines.append(
                    f"- Logs for {service} "
                    "were collected."
                )

    if not lines:

        return (
            "- No additional supporting evidence."
        )

    return "\n".join(
        lines[:10]
    )


# ============================================================
# DETERMINISTIC FALLBACK
# ============================================================

def build_fallback_analysis(
    state: Dict[str, Any]
) -> str:

    root_cause = state.get(
        "root_cause",
        DEFAULT_ROOT_CAUSE
    )

    recommendation = state.get(
        "recommendation",
        DEFAULT_RECOMMENDATION
    )

    diagnostic_evidence = state.get(
        "diagnostic_evidence",
        {}
    )

    confidence = extract_confidence(
        state
    )

    # --------------------------------------------------------
    # Possible causes
    # --------------------------------------------------------

    possible_causes = []

    if isinstance(
        diagnostic_evidence,
        dict
    ):

        causes = diagnostic_evidence.get(
            "possible_causes",
            []
        )

        if isinstance(
            causes,
            list
        ):

            possible_causes = [
                str(cause)
                for cause in causes[:3]
                if cause
            ]

    # --------------------------------------------------------
    # Root cause text
    # --------------------------------------------------------

    root_cause_text = str(
        root_cause
    )

    if not root_cause_text.strip():

        root_cause_text = (
            DEFAULT_ROOT_CAUSE
        )

    if possible_causes:

        root_cause_text += (
            "\n\nPossible causes:\n"
            + "\n".join(
                f"- {cause}"
                for cause in possible_causes
            )
        )

    # --------------------------------------------------------
    # Confidence
    # --------------------------------------------------------

    if (
        confidence["incident"]
        == "NOT_SUPPLIED"
    ):

        incident_confidence_text = (
            "Incident detection confidence "
            "was not supplied."
        )

    else:

        incident_confidence_text = (
            "Incident detection confidence: "
            f"{confidence['incident']}."
        )

    if (
        confidence["root_cause"]
        == "NOT_SUPPLIED"
    ):

        root_confidence_text = (
            "Root cause confidence "
            "was not supplied."
        )

    else:

        root_confidence_text = (
            "Root cause confidence: "
            f"{confidence['root_cause']}."
        )

    # --------------------------------------------------------
    # Final fallback report
    # --------------------------------------------------------

    return (
        "1. Incident Summary\n\n"
        f"{build_incident_summary(state)}\n\n"

        "2. Likely Root Cause\n\n"
        f"{root_cause_text}\n\n"

        "3. Supporting Evidence\n\n"
        f"{build_supporting_evidence(state)}\n\n"

        "4. Impact\n\n"
        f"{DEFAULT_IMPACT}\n\n"

        "5. Recommended Action\n\n"
        f"{recommendation}\n\n"

        "6. Confidence\n\n"
        f"{incident_confidence_text}\n\n"
        f"{root_confidence_text}\n"
    )


# ============================================================
# CALL ONE OPENROUTER MODEL
# ============================================================

def call_model(
    model: str,
    prompt: str
) -> str:

    print(
        f"\nTrying OpenRouter model: {model}"
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        max_tokens=MAX_TOKENS,
        temperature=0,
    )

    if not response.choices:

        raise ValueError(
            "OpenRouter returned no choices."
        )

    choice = response.choices[0]

    finish_reason = getattr(
        choice,
        "finish_reason",
        None
    )

    print(
        f"Finish reason: {finish_reason}"
    )

    # --------------------------------------------------------
    # IMPORTANT:
    # A length finish means the model did not complete
    # the required six-section report.
    # --------------------------------------------------------

    if finish_reason == "length":

        raise ValueError(
            "OpenRouter response was truncated "
            "because the model reached the token limit."
        )

    message = getattr(
        choice,
        "message",
        None
    )

    if message is None:

        raise ValueError(
            "OpenRouter returned no message."
        )

    analysis = getattr(
        message,
        "content",
        None
    )

    if not analysis:

        raise ValueError(
            "OpenRouter returned an empty response."
        )

    analysis = analysis.strip()

    print(
        "\nRaw AI response:"
    )

    print(
        "-" * 70
    )

    print(
        analysis
    )

    print(
        "-" * 70
    )

    # --------------------------------------------------------
    # Validate complete report
    # --------------------------------------------------------

    if not validate_analysis(
        analysis
    ):

        raise ValueError(
            "AI response failed required "
            "section validation."
        )

    return analysis


# ============================================================
# ANALYSE WITH AI
# ============================================================

def analyse_with_ai(
    state: Dict[str, Any]
) -> str:

    prompt = build_ai_prompt(
        state
    )

    print(
        "\nPrompt sent to OpenRouter:"
    )

    print(
        "-" * 70
    )

    print(
        prompt
    )

    print(
        "-" * 70
    )

    # ========================================================
    # PRIMARY MODEL
    # ========================================================

    try:

        return call_model(
            PRIMARY_MODEL,
            prompt
        )

    except Exception as primary_error:

        print(
            "\nPrimary AI model failed:"
        )

        print(
            primary_error
        )

    # ========================================================
    # SECONDARY MODEL
    # ========================================================

    try:

        return call_model(
            SECONDARY_MODEL,
            prompt
        )

    except Exception as secondary_error:

        print(
            "\nSecondary AI model failed:"
        )

        print(
            secondary_error
        )

    # ========================================================
    # BOTH FAILED
    # ========================================================

    raise RuntimeError(
        "All configured OpenRouter models failed."
    )


# ============================================================
# AI ANALYSIS AGENT
# ============================================================

def ai_analysis_agent(
    state: Dict[str, Any]
) -> Dict[str, Any]:

    print(
        "\n[AI Analysis Agent]"
    )

    print(
        "Sending incident data to OpenRouter..."
    )

    try:

        analysis = analyse_with_ai(
            state
        )

        state["ai_analysis"] = analysis

        state.setdefault(
            "messages",
            []
        )

        state["messages"].append(
            "AI incident analysis completed successfully."
        )

        print(
            "\nAI analysis completed successfully."
        )

    except Exception as error:

        print(
            "\nAI analysis request failed:"
        )

        print(
            error
        )

        # ----------------------------------------------------
        # Deterministic fallback
        # ----------------------------------------------------

        fallback = build_fallback_analysis(
            state
        )

        state["ai_analysis"] = fallback

        state.setdefault(
            "messages",
            []
        )

        state["messages"].append(
            "AI analysis failed; deterministic "
            "fallback analysis retained."
        )

        print(
            "\nDeterministic fallback analysis retained."
        )

    return state


# ============================================================
# STANDALONE TEST
# ============================================================

def main():

    print(
        "=" * 70
    )

    print(
        "       AI INCIDENT ANALYSIS AGENT"
    )

    print(
        "=" * 70
    )

    # --------------------------------------------------------
    # Standalone simulated state
    # --------------------------------------------------------

    test_state = {

        "severity": "CRITICAL",

        "incidents": [
            {
                "type": "CPU",

                "pod": (
                    "payment-service-"
                    "77dfdb4b86-bbp65"
                ),

                "severity": "CRITICAL",

                "value": 1.2,

                "message": (
                    "payment-service-"
                    "77dfdb4b86-bbp65 "
                    "CPU usage is critically high"
                ),
            }
        ],

        "root_cause": (
            "The underlying cause cannot be confirmed "
            "from the available evidence."
        ),

        "recommendation": (
            "1. Investigate high CPU usage on "
            "payment-service.\n"
            "2. Check the application's workload "
            "and recent deployment changes.\n"
            "3. Review CPU requests and limits."
        ),

        "evidence": {

            "cpu": {
                (
                    "payment-service-"
                    "77dfdb4b86-bbp65"
                ): 1.2
            },

            "memory": {
                (
                    "payment-service-"
                    "77dfdb4b86-bbp65"
                ): 85.0
            },

            "pods": [
                {
                    "name": (
                        "payment-service-"
                        "77dfdb4b86-bbp65"
                    ),
                    "phase": "Running",
                    "restart_count": 0
                }
            ],

            "events": (
                "Normal Started container "
                "successfully."
            ),

            "logs": {
                "payment-service": (
                    "No additional log evidence "
                    "was supplied."
                )
            }
        },

        "diagnostic_evidence": {

            "possible_causes": [
                "High application workload.",
                "CPU-intensive application processing.",
                "Insufficient CPU resources allocated to the pod.",
            ],

            "root_cause_confidence": "LOW",
        },

        "root_cause_confidence": "LOW",

        "messages": [],
    }

    state = ai_analysis_agent(
        test_state
    )

    print(
        "\n" + "=" * 70
    )

    print(
        "FINAL AI ANALYSIS"
    )

    print(
        "=" * 70
    )

    print(
        state.get(
            "ai_analysis",
            "No AI analysis available."
        )
    )

    print(
        "\n" + "=" * 70
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()