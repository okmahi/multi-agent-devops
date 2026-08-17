import os
import logging
import datetime
from typing import Dict, Any, Optional, List

from kubernetes import client, config
from kubernetes.client.rest import ApiException


# ============================================================
# LOGGING
# ============================================================

logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURATION
# ============================================================

DRY_RUN = (
    os.getenv(
        "DRY_RUN",
        "True"
    ).strip().lower()
    == "true"
)

REMEDIATION_NAMESPACE = os.getenv(
    "REMEDIATION_NAMESPACE",
    "devops-ai"
)

REMEDIATION_TIMEOUT = int(
    os.getenv(
        "REMEDIATION_TIMEOUT",
        "30"
    )
)


# Known services in the DevOps project.
EXPECTED_SERVICES = [
    "user-service",
    "payment-service",
    "inventory-service",
]


logger.info(
    "Remediation initialized with "
    f"DRY_RUN={DRY_RUN}, "
    f"NAMESPACE={REMEDIATION_NAMESPACE}"
)


# ============================================================
# KUBERNETES CONFIGURATION
# ============================================================

def load_kubernetes_config():
    """
    Load Kubernetes configuration.

    In Kubernetes:
        use in-cluster configuration.

    During local development:
        use ~/.kube/config.
    """

    try:

        config.load_incluster_config()

        logger.info(
            "Loaded in-cluster Kubernetes configuration."
        )

    except Exception:

        config.load_kube_config()

        logger.info(
            "Loaded local Kubernetes configuration."
        )


# ============================================================
# HELPER: IDENTIFY KNOWN SERVICE
# ============================================================

def identify_known_service(
    name: str
) -> Optional[str]:
    """
    Identify a known project service from a pod,
    deployment or service name.

    Examples:

        payment-service
            -> payment-service

        payment-service-77dfdb4b86-bbp65
            -> payment-service

        payment-service-test
            -> payment-service

        inventory-service-abc123
            -> inventory-service
    """

    if not name:
        return None

    for service in EXPECTED_SERVICES:

        if (
            name == service
            or name.startswith(
                service + "-"
            )
        ):

            return service

    return None


# ============================================================
# HELPER: EXTRACT DEPLOYMENT NAME
# ============================================================

def extract_deployment_name(
    pod_or_service_name: str
) -> str:
    """
    Extract the deployment/service name from a Kubernetes
    pod name.

    Real Kubernetes Deployment pod:

        payment-service-77dfdb4b86-bbp65

    becomes:

        payment-service

    For known project services, prefix matching is used
    so test/simulated names such as:

        payment-service-test

    are mapped to:

        payment-service
    """

    if not pod_or_service_name:

        return ""

    name = pod_or_service_name.strip()

    # --------------------------------------------------------
    # First use known project service names.
    # --------------------------------------------------------

    known_service = identify_known_service(
        name
    )

    if known_service:

        logger.debug(
            f"Mapped '{name}' to known service "
            f"'{known_service}'."
        )

        return known_service

    # --------------------------------------------------------
    # Generic Kubernetes Deployment pod convention.
    #
    # <deployment>-<replicaset-hash>-<pod-random>
    #
    # Example:
    #
    # payment-service-77dfdb4b86-bbp65
    # --------------------------------------------------------

    parts = name.split("-")

    if len(parts) >= 3:

        replica_set_hash = parts[-2]

        pod_random = parts[-1]

        if (
            len(replica_set_hash) >= 8
            and replica_set_hash.isalnum()
            and len(pod_random) >= 5
            and pod_random.isalnum()
        ):

            deployment_name = "-".join(
                parts[:-2]
            )

            logger.debug(
                f"Extracted deployment "
                f"'{deployment_name}' "
                f"from pod "
                f"'{name}'."
            )

            return deployment_name

    # --------------------------------------------------------
    # Otherwise assume the supplied name is already a
    # deployment/service name.
    # --------------------------------------------------------

    logger.debug(
        f"No Kubernetes pod suffix detected in "
        f"'{name}'. Using name directly."
    )

    return name


# ============================================================
# HELPER: BUILD RESTART PATCH
# ============================================================

def build_restart_patch() -> Dict[str, Any]:
    """
    Build the Kubernetes annotation patch used to trigger
    a Deployment rollout restart.
    """

    timestamp = (
        datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat()
    )

    return {
        "spec": {
            "template": {
                "metadata": {
                    "annotations": {
                        "kubectl.kubernetes.io/restartedAt":
                            timestamp
                    }
                }
            }
        }
    }


# ============================================================
# ROLLOUT RESTART DEPLOYMENT
# ============================================================

def rollout_restart_deployment(
    deployment_name: str,
    namespace: str = REMEDIATION_NAMESPACE
) -> Dict[str, Any]:
    """
    Restart a Kubernetes Deployment.

    In LIVE mode:
        The Deployment is patched.

    In DRY_RUN mode:
        No Kubernetes modification is made.

    Returns a structured remediation result.
    """

    if not deployment_name:

        return {
            "status": "ERROR",
            "message": (
                "Deployment name was not provided."
            ),
            "deployment": deployment_name,
            "namespace": namespace,
            "executed": False,
            "mode": (
                "DRY_RUN"
                if DRY_RUN
                else "LIVE"
            ),
        }

    patch_body = build_restart_patch()

    # ========================================================
    # LOAD KUBERNETES CONFIG
    # ========================================================

    try:

        load_kubernetes_config()

        apps_api = client.AppsV1Api()

    except Exception as error:

        error_message = (
            "Failed to load Kubernetes configuration: "
            f"{str(error)}"
        )

        logger.error(
            error_message
        )

        return {
            "status": "ERROR",
            "message": error_message,
            "deployment": deployment_name,
            "namespace": namespace,
            "executed": False,
            "mode": (
                "DRY_RUN"
                if DRY_RUN
                else "LIVE"
            ),
        }

    # ========================================================
    # CHECK DEPLOYMENT
    # ========================================================

    try:

        logger.info(
            f"Checking deployment "
            f"'{deployment_name}' "
            f"in namespace "
            f"'{namespace}'."
        )

        deployment = (
            apps_api.read_namespaced_deployment(
                name=deployment_name,
                namespace=namespace
            )
        )

        replicas_before = (
            deployment.spec.replicas
            if deployment.spec.replicas is not None
            else 0
        )

        logger.info(
            f"Deployment found: "
            f"{deployment_name}"
        )

        logger.info(
            f"Replicas before remediation: "
            f"{replicas_before}"
        )

    except ApiException as error:

        error_message = (
            f"Kubernetes API error: "
            f"{error.status} - "
            f"{error.reason}"
        )

        # ----------------------------------------------------
        # DRY_RUN behaviour
        #
        # During a simulated/test run, the supplied pod may
        # not actually exist in Kubernetes.
        #
        # We should not report this as a remediation failure
        # when DRY_RUN is enabled.
        # ----------------------------------------------------

        if (
            DRY_RUN
            and error.status == 404
        ):

            logger.warning(
                f"[DRY_RUN] Deployment "
                f"'{deployment_name}' "
                f"was not found. "
                f"No Kubernetes change will be made."
            )

            return {
                "status": "DRY_RUN",
                "message": (
                    f"Dry-run: Deployment "
                    f"'{deployment_name}' "
                    f"was not found, so no "
                    f"Kubernetes change was applied."
                ),
                "deployment": deployment_name,
                "namespace": namespace,
                "replicas_before": None,
                "replicas_after": None,
                "executed": False,
                "mode": "DRY_RUN",
                "patch_body": patch_body,
                "kubernetes_lookup": "NOT_FOUND",
            }

        logger.error(
            error_message
        )

        return {
            "status": "ERROR",
            "message": error_message,
            "deployment": deployment_name,
            "namespace": namespace,
            "executed": False,
            "mode": (
                "DRY_RUN"
                if DRY_RUN
                else "LIVE"
            ),
            "error_code": error.status,
        }

    except Exception as error:

        error_message = (
            f"Unexpected Kubernetes lookup error: "
            f"{str(error)}"
        )

        logger.error(
            error_message
        )

        return {
            "status": "ERROR",
            "message": error_message,
            "deployment": deployment_name,
            "namespace": namespace,
            "executed": False,
            "mode": (
                "DRY_RUN"
                if DRY_RUN
                else "LIVE"
            ),
        }

    # ========================================================
    # DRY RUN
    # ========================================================

    if DRY_RUN:

        logger.warning(
            f"[DRY_RUN] Would restart deployment "
            f"'{deployment_name}'."
        )

        return {
            "status": "DRY_RUN",
            "message": (
                f"Dry-run: Would restart "
                f"deployment "
                f"'{deployment_name}'. "
                f"No Kubernetes changes were applied."
            ),
            "deployment": deployment_name,
            "namespace": namespace,
            "replicas_before": replicas_before,
            "replicas_after": replicas_before,
            "executed": False,
            "mode": "DRY_RUN",
            "patch_body": patch_body,
        }

    # ========================================================
    # LIVE REMEDIATION
    # ========================================================

    try:

        logger.warning(
            f"[LIVE] Executing rollout restart "
            f"for deployment "
            f"'{deployment_name}'."
        )

        patched_deployment = (
            apps_api.patch_namespaced_deployment(
                name=deployment_name,
                namespace=namespace,
                body=patch_body
            )
        )

        replicas_after = (
            patched_deployment.spec.replicas
            if patched_deployment.spec.replicas is not None
            else 0
        )

        logger.info(
            f"Deployment "
            f"'{deployment_name}' "
            f"patched successfully."
        )

        return {
            "status": "SUCCESS",
            "message": (
                f"Successfully restarted "
                f"deployment "
                f"'{deployment_name}'."
            ),
            "deployment": deployment_name,
            "namespace": namespace,
            "replicas_before": replicas_before,
            "replicas_after": replicas_after,
            "executed": True,
            "mode": "LIVE",
            "patch_body": patch_body,
        }

    except ApiException as error:

        error_message = (
            f"Kubernetes API error during remediation: "
            f"{error.status} - "
            f"{error.reason}"
        )

        logger.error(
            error_message
        )

        return {
            "status": "ERROR",
            "message": error_message,
            "deployment": deployment_name,
            "namespace": namespace,
            "replicas_before": replicas_before,
            "replicas_after": replicas_before,
            "executed": False,
            "mode": "LIVE",
            "error_code": error.status,
            "patch_body": patch_body,
        }

    except Exception as error:

        error_message = (
            f"Unexpected remediation error: "
            f"{str(error)}"
        )

        logger.error(
            error_message
        )

        return {
            "status": "ERROR",
            "message": error_message,
            "deployment": deployment_name,
            "namespace": namespace,
            "replicas_before": replicas_before,
            "replicas_after": replicas_before,
            "executed": False,
            "mode": "LIVE",
            "patch_body": patch_body,
        }


# ============================================================
# REMEDIATION AGENT
# ============================================================

def remediation_agent(
    state: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Remediation Agent.

    Reads incidents from LangGraph state and performs
    incident-specific Kubernetes remediation.

    IMPORTANT STATE CONTRACT:

        state["remediation"]

    is the single source of truth for the Verification Agent.

    Verification Agent must NOT depend on another key such as:

        state["remediation_results"]
    """

    logger.info(
        "=== REMEDIATION AGENT STARTED ==="
    )

    print(
        "\n[Remediation Agent]"
    )

    # ========================================================
    # READ INCIDENTS
    # ========================================================

    incidents = state.get(
        "incidents",
        []
    )

    if not isinstance(
        incidents,
        list
    ):

        incidents = []

    # ========================================================
    # REMEDIATION ATTEMPT
    # ========================================================

    current_attempt = state.get(
        "remediation_attempt",
        0
    )

    try:

        current_attempt = int(
            current_attempt
        )

    except (
        TypeError,
        ValueError
    ):

        current_attempt = 0

    current_attempt += 1

    state["remediation_attempt"] = (
        current_attempt
    )

    logger.info(
        f"Remediation attempt: "
        f"{current_attempt}"
    )

    # ========================================================
    # NO INCIDENTS
    # ========================================================

    if not incidents:

        remediation = {
            "status": "NO_INCIDENTS",
            "message": (
                "No incidents detected. "
                "No remediation required."
            ),
            "mode": (
                "DRY_RUN"
                if DRY_RUN
                else "LIVE"
            ),
            "executed": False,
            "attempt": current_attempt,
            "target_pod": None,
            "target_service": None,
            "deployment": None,
            "replicas_before": None,
            "replicas_after": None,
            "count": 0,
            "total": 0,
            "results": [],
        }

        # ----------------------------------------------------
        # SINGLE SOURCE OF TRUTH
        # ----------------------------------------------------

        state["remediation"] = (
            remediation
        )

        state.setdefault(
            "messages",
            []
        )

        state["messages"].append(
            "Remediation: No incidents to remediate."
        )

        print(
            "No incidents to remediate."
        )

        return state

    # ========================================================
    # PROCESS INCIDENTS
    # ========================================================

    results: List[Dict[str, Any]] = []

    success_count = 0

    target_pod = None

    target_service = None

    deployment_name = None

    replicas_before = None

    replicas_after = None

    # ========================================================
    # EACH INCIDENT
    # ========================================================

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

        pod_name = incident.get(
            "pod",
            ""
        )

        service_name = incident.get(
            "service"
        )

        severity = incident.get(
            "severity",
            "UNKNOWN"
        )

        # ----------------------------------------------------
        # DETERMINE TARGET
        # ----------------------------------------------------

        if pod_name:

            target_pod = pod_name

            deployment_name = (
                extract_deployment_name(
                    pod_name
                )
            )

            target_service = (
                identify_known_service(
                    deployment_name
                )
                or deployment_name
            )

        elif service_name:

            target_service = (
                identify_known_service(
                    service_name
                )
                or service_name
            )

            deployment_name = (
                target_service
            )

        else:

            deployment_name = ""

        logger.info(
            f"Incident target: "
            f"pod={pod_name}, "
            f"service={target_service}, "
            f"deployment={deployment_name}"
        )

        # ----------------------------------------------------
        # INVALID TARGET
        # ----------------------------------------------------

        if not deployment_name:

            result = {
                "incident_type": incident_type,
                "original_pod": pod_name,
                "target_service": target_service,
                "severity": severity,
                "status": "ERROR",
                "message": (
                    "Could not determine "
                    "target deployment."
                ),
                "executed": False,
                "mode": (
                    "DRY_RUN"
                    if DRY_RUN
                    else "LIVE"
                ),
            }

            results.append(
                result
            )

            continue

        # ----------------------------------------------------
        # SUPPORTED INCIDENT TYPES
        # ----------------------------------------------------

        if incident_type in [
            "CPU",
            "MEMORY",
            "AVAILABILITY",
        ]:

            logger.info(
                f"Remediating "
                f"{incident_type} incident "
                f"on deployment "
                f"{deployment_name}."
            )

            result = (
                rollout_restart_deployment(
                    deployment_name=deployment_name,
                    namespace=REMEDIATION_NAMESPACE,
                )
            )

        else:

            result = {
                "status": "ERROR",
                "message": (
                    f"Unknown incident type: "
                    f"{incident_type}"
                ),
                "deployment": deployment_name,
                "namespace": REMEDIATION_NAMESPACE,
                "executed": False,
                "mode": (
                    "DRY_RUN"
                    if DRY_RUN
                    else "LIVE"
                ),
            }

        # ----------------------------------------------------
        # ADD INCIDENT METADATA
        # ----------------------------------------------------

        result["incident_type"] = (
            incident_type
        )

        result["original_pod"] = (
            pod_name
        )

        result["target_service"] = (
            target_service
        )

        result["severity"] = (
            severity
        )

        results.append(
            result
        )

        # ----------------------------------------------------
        # COUNT SUCCESSFUL / DRY-RUN ACTIONS
        # ----------------------------------------------------

        if result.get(
            "status"
        ) in [
            "SUCCESS",
            "DRY_RUN",
        ]:

            success_count += 1

        # ----------------------------------------------------
        # CAPTURE REPLICA INFORMATION
        # ----------------------------------------------------

        if result.get(
            "replicas_before"
        ) is not None:

            replicas_before = (
                result.get(
                    "replicas_before"
                )
            )

        if result.get(
            "replicas_after"
        ) is not None:

            replicas_after = (
                result.get(
                    "replicas_after"
                )
            )

    # ========================================================
    # DETERMINE OVERALL STATUS
    # ========================================================

    total_incidents = len(
        incidents
    )

    dry_run_count = sum(
        1
        for result in results
        if result.get("status") == "DRY_RUN"
    )

    live_success_count = sum(
        1
        for result in results
        if result.get("status") == "SUCCESS"
    )

    error_count = sum(
        1
        for result in results
        if result.get("status") == "ERROR"
    )

    # --------------------------------------------------------
    # ALL ACTIONS WERE DRY RUN
    # --------------------------------------------------------

    if (
        dry_run_count == total_incidents
        and total_incidents > 0
    ):

        overall_status = "DRY_RUN"

        overall_message = (
            f"{dry_run_count}/"
            f"{total_incidents} remediation "
            f"actions simulated successfully. "
            f"No Kubernetes changes were applied."
        )

        overall_executed = False

    # --------------------------------------------------------
    # ALL LIVE ACTIONS SUCCEEDED
    # --------------------------------------------------------

    elif (
        live_success_count == total_incidents
        and total_incidents > 0
    ):

        overall_status = "SUCCESS"

        overall_message = (
            f"{live_success_count}/"
            f"{total_incidents} remediation "
            f"actions executed successfully."
        )

        overall_executed = True

    # --------------------------------------------------------
    # PARTIAL SUCCESS
    # --------------------------------------------------------

    elif (
        success_count > 0
        and error_count > 0
    ):

        overall_status = (
            "PARTIAL_SUCCESS"
        )

        overall_message = (
            f"{success_count}/"
            f"{total_incidents} remediation "
            f"actions completed successfully."
        )

        overall_executed = (
            live_success_count > 0
        )

    # --------------------------------------------------------
    # FAILED
    # --------------------------------------------------------

    else:

        overall_status = "FAILED"

        overall_message = (
            f"0/{total_incidents} remediation "
            f"actions completed successfully."
        )

        overall_executed = False

    # ========================================================
    # BUILD FINAL REMEDIATION STATE
    # ========================================================

    remediation = {

        "status":
            overall_status,

        "message":
            overall_message,

        "mode":
            (
                "DRY_RUN"
                if DRY_RUN
                else "LIVE"
            ),

        "executed":
            overall_executed,

        "attempt":
            current_attempt,

        "target_pod":
            target_pod,

        "target_service":
            target_service,

        "deployment":
            deployment_name,

        "namespace":
            REMEDIATION_NAMESPACE,

        "replicas_before":
            replicas_before,

        "replicas_after":
            replicas_after,

        "count":
            success_count,

        "total":
            total_incidents,

        "results":
            results,
    }

    # ========================================================
    # CRITICAL STATE CONTRACT
    # ========================================================
    #
    # Verification Agent reads:
    #
    #     state["remediation"]
    #
    # Therefore this is the ONLY remediation result
    # written to LangGraph state.
    # ========================================================

    state["remediation"] = (
        remediation
    )

    # ========================================================
    # MESSAGES
    # ========================================================

    state.setdefault(
        "messages",
        []
    )

    state["messages"].append(
        "Remediation attempt "
        f"{current_attempt} completed: "
        f"{success_count}/"
        f"{total_incidents} "
        "actions completed."
    )

    # ========================================================
    # DISPLAY
    # ========================================================

    print(
        f"\nRemediation attempt: "
        f"{current_attempt}"
    )

    print(
        f"Status: "
        f"{overall_status}"
    )

    print(
        f"Mode: "
        f"{remediation['mode']}"
    )

    print(
        f"Executed: "
        f"{remediation['executed']}"
    )

    print(
        f"Target service: "
        f"{target_service}"
    )

    print(
        f"Target deployment: "
        f"{deployment_name}"
    )

    print(
        f"Message: "
        f"{overall_message}"
    )

    # --------------------------------------------------------
    # Display individual results
    # --------------------------------------------------------

    for result in results:

        print(
            "\n  Incident Type: "
            f"{result.get('incident_type')}"
        )

        print(
            "  Original Pod: "
            f"{result.get('original_pod')}"
        )

        print(
            "  Target Service: "
            f"{result.get('target_service')}"
        )

        print(
            "  Deployment: "
            f"{result.get('deployment', 'N/A')}"
        )

        print(
            "  Status: "
            f"{result.get('status')}"
        )

        print(
            "  Executed: "
            f"{result.get('executed')}"
        )

        print(
            "  Message: "
            f"{result.get('message')}"
        )

    # ========================================================
    # DEBUG: VERIFY STATE CONTRACT
    # ========================================================

    print(
        "\n[Remediation Agent]"
    )

    print(
        "Final remediation state:"
    )

    print(
        state.get(
            "remediation",
            {}
        )
    )

    logger.info(
        "=== REMEDIATION AGENT COMPLETED ==="
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
        "       REMEDIATION AGENT TEST"
    )

    print(
        "=" * 70
    )

    print(
        f"\nDRY_RUN={DRY_RUN}"
    )

    test_state = {

        "messages": [],

        "incident_detected": True,

        "incidents": [

            {
                "type": "CPU",

                "pod": (
                    "payment-service-"
                    "77dfdb4b86-bbp65"
                ),

                "severity": "CRITICAL",

                "value": 0.95,

                "message": (
                    "payment-service CPU "
                    "usage is critically high."
                ),
            }
        ],

        "remediation_attempt": 0,
    }

    final_state = remediation_agent(
        test_state
    )

    print(
        "\n" + "=" * 70
    )

    print(
        "FINAL REMEDIATION STATE"
    )

    print(
        "=" * 70
    )

    print(
        final_state.get(
            "remediation"
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