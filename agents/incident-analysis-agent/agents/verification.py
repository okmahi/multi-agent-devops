from typing import Dict, Any

import time
import sys
from pathlib import Path

from kubernetes import client, config


# ============================================================
# LOCATE MONITORING AGENT
# ============================================================

PHASE4_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "monitoring-agent"
)

if str(PHASE4_DIR) not in sys.path:

    sys.path.insert(
        0,
        str(PHASE4_DIR)
    )


from evidence_collector import (
    collect_cpu_usage,
    collect_memory_usage,
)


# ============================================================
# CONFIGURATION
# ============================================================

NAMESPACE = "devops-ai"

VERIFICATION_TIMEOUT = 60

VERIFICATION_INTERVAL = 5

CPU_WARNING_THRESHOLD = 0.50

CPU_CRITICAL_THRESHOLD = 0.80

MEMORY_WARNING_THRESHOLD_MB = 100

MEMORY_CRITICAL_THRESHOLD_MB = 200


# ============================================================
# KUBERNETES CONFIGURATION
# ============================================================

def load_kubernetes_config():

    try:

        config.load_incluster_config()

        print(
            "Loaded in-cluster Kubernetes configuration."
        )

    except Exception:

        config.load_kube_config()

        print(
            "Loaded local Kubernetes configuration."
        )


# ============================================================
# KUBERNETES CLIENT
# ============================================================

def get_apps_api():

    load_kubernetes_config()

    return client.AppsV1Api()


def get_core_api():

    load_kubernetes_config()

    return client.CoreV1Api()


# ============================================================
# IDENTIFY SERVICE
# ============================================================

def identify_service(
    target_name: str
):

    if not target_name:

        return None

    known_services = [

        "payment-service",

        "user-service",

        "inventory-service",

    ]

    for service in known_services:

        if (
            target_name == service
            or target_name.startswith(
                service + "-"
            )
        ):

            return service

    return None


# ============================================================
# WAIT FOR DEPLOYMENT READY
# ============================================================

def wait_for_deployment_ready(
    apps_api,
    deployment_name: str,
    namespace: str,
    timeout: int = VERIFICATION_TIMEOUT,
    interval: int = VERIFICATION_INTERVAL,
):

    start_time = time.time()

    while True:

        deployment = (
            apps_api.read_namespaced_deployment(
                name=deployment_name,
                namespace=namespace
            )
        )

        desired = (
            deployment.spec.replicas
            if deployment.spec.replicas
            is not None
            else 0
        )

        ready = (
            deployment.status.ready_replicas
            if deployment.status.ready_replicas
            is not None
            else 0
        )

        available = (
            deployment.status.available_replicas
            if deployment.status.available_replicas
            is not None
            else 0
        )

        print(
            "\nDeployment readiness:"
        )

        print(
            f"  Desired: {desired}"
        )

        print(
            f"  Ready: {ready}"
        )

        print(
            f"  Available: {available}"
        )

        if (
            desired > 0
            and ready == desired
            and available == desired
        ):

            return (
                deployment,
                True
            )

        elapsed = (
            time.time()
            - start_time
        )

        if elapsed >= timeout:

            return (
                deployment,
                False
            )

        time.sleep(
            interval
        )


# ============================================================
# GET CURRENT RUNNING PODS
# ============================================================

def get_current_pods(
    core_api,
    target_service: str
):

    if not target_service:

        return []

    pod_list = (
        core_api.list_namespaced_pod(
            namespace=NAMESPACE,
            label_selector=(
                f"app={target_service}"
            )
        )
    )

    current_pods = []

    for pod in pod_list.items:

        pod_name = (
            pod.metadata.name
        )

        phase = (
            pod.status.phase
            if pod.status
            else "Unknown"
        )

        if phase == "Running":

            current_pods.append(
                pod_name
            )

    return current_pods


# ============================================================
# WAIT FOR CURRENT PROMETHEUS METRICS
# ============================================================

def wait_for_recovery_metrics(
    target_service: str,
    current_pods,
    timeout: int = VERIFICATION_TIMEOUT,
    interval: int = VERIFICATION_INTERVAL,
):

    start_time = time.time()

    while True:

        try:

            cpu_data = (
                collect_cpu_usage()
            )

            memory_data = (
                collect_memory_usage()
            )

            # ------------------------------------------------
            # IMPORTANT:
            #
            # Only use metrics belonging to CURRENT
            # Kubernetes pods.
            #
            # This prevents stale Prometheus metrics from
            # deleted pods being treated as active.
            # ------------------------------------------------

            service_cpu = {

                pod: value

                for pod, value
                in cpu_data.items()

                if pod in current_pods

            }

            service_memory = {

                pod: value

                for pod, value
                in memory_data.items()

                if pod in current_pods

            }

            print(
                "\nFresh Prometheus metrics "
                "for CURRENT Kubernetes pods:"
            )

            for pod in current_pods:

                if pod in service_cpu:

                    print(
                        f"  {pod}: "
                        f"CPU="
                        f"{service_cpu[pod]:.3f} "
                        f"cores"
                    )

                else:

                    print(
                        f"  {pod}: "
                        "CPU metric not available yet"
                    )

            for pod in current_pods:

                if pod in service_memory:

                    print(
                        f"  {pod}: "
                        f"Memory="
                        f"{service_memory[pod]:.2f} MB"
                    )

            # ------------------------------------------------
            # Require CPU metrics before making a recovery
            # decision.
            # ------------------------------------------------

            if service_cpu:

                return (
                    service_cpu,
                    service_memory
                )

        except Exception as error:

            print(
                "\nWaiting for Prometheus metrics:"
            )

            print(
                error
            )

        elapsed = (
            time.time()
            - start_time
        )

        if elapsed >= timeout:

            return (
                {},
                {}
            )

        time.sleep(
            interval
        )


# ============================================================
# CHECK RESOURCE RECOVERY
# ============================================================

def check_resource_recovery(
    incidents,
    cpu_data,
    memory_data,
    current_pods
):

    findings = []

    recovery_conditions = []

    for incident in incidents:

        incident_type = incident.get(
            "type"
        )

        original_pod = incident.get(
            "pod"
        )

        # ====================================================
        # CPU
        # ====================================================

        if incident_type == "CPU":

            if not cpu_data:

                recovery_conditions.append(
                    False
                )

                findings.append(
                    "Current CPU metrics are "
                    "not available."
                )

                continue

            current_values = [

                value

                for value in cpu_data.values()

                if isinstance(
                    value,
                    (int, float)
                )

            ]

            if not current_values:

                recovery_conditions.append(
                    False
                )

                findings.append(
                    "No valid current CPU metric "
                    "values were available."
                )

                continue

            max_cpu = max(
                current_values
            )

            findings.append(
                f"Maximum current CPU usage: "
                f"{max_cpu:.3f} cores."
            )

            if max_cpu < CPU_CRITICAL_THRESHOLD:

                recovery_conditions.append(
                    True
                )

                findings.append(
                    "Current CPU usage is below "
                    f"the critical threshold of "
                    f"{CPU_CRITICAL_THRESHOLD:.2f} cores."
                )

            else:

                recovery_conditions.append(
                    False
                )

                findings.append(
                    "Current CPU usage remains at "
                    f"or above the critical threshold "
                    f"of {CPU_CRITICAL_THRESHOLD:.2f} cores."
                )

        # ====================================================
        # MEMORY
        # ====================================================

        elif incident_type == "MEMORY":

            if not memory_data:

                recovery_conditions.append(
                    False
                )

                findings.append(
                    "Current memory metrics are "
                    "not available."
                )

                continue

            current_values = [

                value

                for value in memory_data.values()

                if isinstance(
                    value,
                    (int, float)
                )

            ]

            if not current_values:

                recovery_conditions.append(
                    False
                )

                findings.append(
                    "No valid current memory metric "
                    "values were available."
                )

                continue

            max_memory = max(
                current_values
            )

            findings.append(
                f"Maximum current memory usage: "
                f"{max_memory:.2f} MB."
            )

            if (
                max_memory
                < MEMORY_CRITICAL_THRESHOLD_MB
            ):

                recovery_conditions.append(
                    True
                )

                findings.append(
                    "Current memory usage is below "
                    f"the critical threshold of "
                    f"{MEMORY_CRITICAL_THRESHOLD_MB} MB."
                )

            else:

                recovery_conditions.append(
                    False
                )

                findings.append(
                    "Current memory usage remains at "
                    f"or above the critical threshold "
                    f"of {MEMORY_CRITICAL_THRESHOLD_MB} MB."
                )

        # ====================================================
        # AVAILABILITY
        # ====================================================

        elif incident_type == "AVAILABILITY":

            # ------------------------------------------------
            # Availability is determined using CURRENT
            # Kubernetes pods, not Prometheus CPU data.
            # ------------------------------------------------

            if current_pods:

                recovery_conditions.append(
                    True
                )

                findings.append(
                    f"Availability recovered: "
                    f"{len(current_pods)} current "
                    f"running pod(s) detected."
                )

                if original_pod:

                    if original_pod in current_pods:

                        findings.append(
                            f"Original pod "
                            f"{original_pod} "
                            "is still running."
                        )

                    else:

                        findings.append(
                            f"Original pod "
                            f"{original_pod} was replaced "
                            "by a current running pod."
                        )

            else:

                recovery_conditions.append(
                    False
                )

                findings.append(
                    "No current running pods were "
                    "detected for the affected service."
                )

        # ====================================================
        # UNKNOWN INCIDENT
        # ====================================================

        else:

            recovery_conditions.append(
                False
            )

            findings.append(
                f"Unsupported incident type: "
                f"{incident_type}"
            )

    if not recovery_conditions:

        return (
            False,
            findings
        )

    recovered = all(
        recovery_conditions
    )

    return (
        recovered,
        findings
    )


# ============================================================
# STORE VERIFICATION RESULT
# ============================================================

def store_verification(
    state: Dict[str, Any],
    status: str,
    result: str,
    confidence: str,
    remediation_mode: str,
    remediation_executed: bool,
    remediation_status: str,
    target_pod,
    target_service,
    deployment_name,
    replicas_before,
    replicas_after,
    findings,
    current_pods=None,
    cpu_data=None,
    memory_data=None,
):

    verification = {

        "status":
            status,

        "result":
            result,

        "confidence":
            confidence,

        "remediation_mode":
            remediation_mode,

        "remediation_executed":
            remediation_executed,

        "remediation_status":
            remediation_status,

        "target_pod":
            target_pod,

        "target_service":
            target_service,

        "deployment":
            deployment_name,

        "replicas_before":
            replicas_before,

        "replicas_after":
            replicas_after,

        "current_pods":
            current_pods or [],

        "cpu":
            cpu_data or {},

        "memory":
            memory_data or {},

        "findings":
            findings

    }

    state["verification"] = (
        verification
    )

    state["verification_status"] = (
        status
    )

    state["verification_result"] = (
        result
    )

    state["verification_confidence"] = (
        confidence
    )

    state["verification_findings"] = (
        findings
    )

    state.setdefault(
        "messages",
        []
    )

    state["messages"].append(
        f"Verification completed: "
        f"{status}."
    )

    return state


# ============================================================
# VERIFICATION AGENT
# ============================================================

def verification_agent(
    state: Dict[str, Any]
) -> Dict[str, Any]:

    print(
        "\n[Verification Agent]"
    )

    print(
        "Verifying incident recovery..."
    )

    incidents = state.get(
        "incidents",
        []
    )

    # ========================================================
    # IMPORTANT STATE CONTRACT
    #
    # Remediation Agent writes:
    #
    #     state["remediation"]
    #
    # Verification Agent reads:
    #
    #     state["remediation"]
    #
    # This removes the previous state mismatch.
    # ========================================================

    remediation = state.get(
        "remediation",
        {}
    )

    remediation_mode = remediation.get(
        "mode",
        "UNKNOWN"
    )

    remediation_executed = remediation.get(
        "executed",
        False
    )

    remediation_status = remediation.get(
        "status",
        "UNKNOWN"
    )

    target_service = remediation.get(
        "target_service"
    )

    target_pod = remediation.get(
        "target_pod"
    )

    deployment_name = remediation.get(
        "deployment"
    )

    replicas_before = remediation.get(
        "replicas_before"
    )

    replicas_after = remediation.get(
        "replicas_after"
    )

    remediation_attempt = state.get(
        "remediation_attempt",
        0
    )

    findings = []

    # ========================================================
    # IDENTIFY TARGET
    # ========================================================

    if not target_pod and incidents:

        target_pod = incidents[0].get(
            "pod"
        )

    if not target_service:

        target_service = identify_service(
            target_pod
        )

    if not deployment_name:

        deployment_name = (
            target_service
        )

    # ========================================================
    # TARGET INFORMATION
    # ========================================================

    if target_pod:

        findings.append(
            f"Original target pod: "
            f"{target_pod}"
        )

    if target_service:

        findings.append(
            f"Target service: "
            f"{target_service}"
        )

    if deployment_name:

        findings.append(
            f"Target deployment: "
            f"{deployment_name}"
        )

    findings.append(
        f"Remediation mode: "
        f"{remediation_mode}"
    )

    findings.append(
        f"Remediation status: "
        f"{remediation_status}"
    )

    findings.append(
        f"Remediation attempt: "
        f"{remediation_attempt}"
    )

    # ========================================================
    # NO INCIDENT
    # ========================================================

    if not incidents:

        status = "RECOVERED"

        result = (
            "No incident was present for verification."
        )

        confidence = "HIGH"

        return store_verification(
            state=state,
            status=status,
            result=result,
            confidence=confidence,
            remediation_mode=remediation_mode,
            remediation_executed=remediation_executed,
            remediation_status=remediation_status,
            target_pod=target_pod,
            target_service=target_service,
            deployment_name=deployment_name,
            replicas_before=replicas_before,
            replicas_after=replicas_after,
            findings=findings,
        )

    # ========================================================
    # DRY RUN
    # ========================================================

    if remediation_mode == "DRY_RUN":

        status = "NOT_VERIFIED"

        result = (
            "Recovery cannot be confirmed because "
            "remediation is running in DRY_RUN mode."
        )

        confidence = "HIGH"

        findings.append(
            "No Kubernetes modification was performed "
            "because DRY_RUN is enabled."
        )

        state = store_verification(
            state=state,
            status=status,
            result=result,
            confidence=confidence,
            remediation_mode=remediation_mode,
            remediation_executed=remediation_executed,
            remediation_status=remediation_status,
            target_pod=target_pod,
            target_service=target_service,
            deployment_name=deployment_name,
            replicas_before=replicas_before,
            replicas_after=replicas_after,
            findings=findings,
        )

        print(
            f"\nVerification Status: "
            f"{status}"
        )

        print(
            f"Verification Result: "
            f"{result}"
        )

        print(
            f"Confidence: "
            f"{confidence}"
        )

        return state

    # ========================================================
    # REMEDIATION FAILED / PARTIAL
    # ========================================================

    if remediation_status in [
        "FAILED",
        "ERROR",
        "PARTIAL_SUCCESS",
    ]:

        status = "NOT_RECOVERED"

        result = (
            "Recovery cannot be confirmed because "
            "the remediation action did not complete "
            "successfully for all detected incidents."
        )

        confidence = "HIGH"

        findings.append(
            "Remediation did not complete successfully "
            "for all required actions."
        )

        state = store_verification(
            state=state,
            status=status,
            result=result,
            confidence=confidence,
            remediation_mode=remediation_mode,
            remediation_executed=remediation_executed,
            remediation_status=remediation_status,
            target_pod=target_pod,
            target_service=target_service,
            deployment_name=deployment_name,
            replicas_before=replicas_before,
            replicas_after=replicas_after,
            findings=findings,
        )

        return state

    # ========================================================
    # REMEDIATION NOT EXECUTED
    # ========================================================

    if not remediation_executed:

        status = "NOT_VERIFIED"

        result = (
            "Recovery cannot be confirmed because "
            "the remediation action was not executed."
        )

        confidence = "HIGH"

        findings.append(
            "Remediation was not executed."
        )

        state = store_verification(
            state=state,
            status=status,
            result=result,
            confidence=confidence,
            remediation_mode=remediation_mode,
            remediation_executed=remediation_executed,
            remediation_status=remediation_status,
            target_pod=target_pod,
            target_service=target_service,
            deployment_name=deployment_name,
            replicas_before=replicas_before,
            replicas_after=replicas_after,
            findings=findings,
        )

        return state

    # ========================================================
    # KUBERNETES VERIFICATION
    # ========================================================

    try:

        apps_api = get_apps_api()

        core_api = get_core_api()

        if not target_service:

            raise RuntimeError(
                "Target service could not be identified."
            )

        if not deployment_name:

            deployment_name = (
                target_service
            )

        # ====================================================
        # WAIT FOR DEPLOYMENT
        # ====================================================

        print(
            "\nWaiting for Kubernetes "
            "deployment readiness..."
        )

        deployment, replica_health = (
            wait_for_deployment_ready(

                apps_api=apps_api,

                deployment_name=(
                    deployment_name
                ),

                namespace=NAMESPACE

            )
        )

        desired_replicas = (
            deployment.spec.replicas
            if deployment.spec.replicas
            is not None
            else 0
        )

        ready_replicas = (
            deployment.status.ready_replicas
            if deployment.status.ready_replicas
            is not None
            else 0
        )

        available_replicas = (
            deployment.status.available_replicas
            if deployment.status.available_replicas
            is not None
            else 0
        )

        findings.append(
            f"Deployment desired replicas: "
            f"{desired_replicas}."
        )

        findings.append(
            f"Deployment ready replicas: "
            f"{ready_replicas}."
        )

        findings.append(
            f"Deployment available replicas: "
            f"{available_replicas}."
        )

        # ====================================================
        # DEPLOYMENT NOT READY
        # ====================================================

        if not replica_health:

            status = "RECOVERY_PENDING"

            result = (
                "Deployment did not reach the "
                "desired ready state within "
                f"{VERIFICATION_TIMEOUT} seconds."
            )

            confidence = "HIGH"

            findings.append(
                "Deployment readiness requirement "
                "was not satisfied."
            )

            return store_verification(
                state=state,
                status=status,
                result=result,
                confidence=confidence,
                remediation_mode=remediation_mode,
                remediation_executed=remediation_executed,
                remediation_status=remediation_status,
                target_pod=target_pod,
                target_service=target_service,
                deployment_name=deployment_name,
                replicas_before=replicas_before,
                replicas_after=replicas_after,
                findings=findings,
            )

        # ====================================================
        # CURRENT PODS
        # ====================================================

        current_pods = get_current_pods(
            core_api,
            target_service
        )

        findings.append(
            f"Current running pods: "
            f"{len(current_pods)}."
        )

        for pod in current_pods:

            findings.append(
                f"Current running pod: "
                f"{pod}"
            )

        # ====================================================
        # NO CURRENT PODS
        # ====================================================

        if not current_pods:

            status = "RECOVERY_PENDING"

            result = (
                "Deployment is ready, but no current "
                "running pods were found for the "
                "affected service."
            )

            confidence = "HIGH"

            findings.append(
                "No current running Kubernetes "
                "pods were detected."
            )

            return store_verification(
                state=state,
                status=status,
                result=result,
                confidence=confidence,
                remediation_mode=remediation_mode,
                remediation_executed=remediation_executed,
                remediation_status=remediation_status,
                target_pod=target_pod,
                target_service=target_service,
                deployment_name=deployment_name,
                replicas_before=replicas_before,
                replicas_after=replicas_after,
                findings=findings,
                current_pods=current_pods,
            )

        # ====================================================
        # CURRENT PROMETHEUS METRICS
        # ====================================================

        print(
            "\nWaiting for fresh Prometheus "
            "metrics..."
        )

        cpu_data, memory_data = (
            wait_for_recovery_metrics(

                target_service=(
                    target_service
                ),

                current_pods=(
                    current_pods
                )

            )
        )

        # ====================================================
        # METRICS UNAVAILABLE
        # ====================================================

        if not cpu_data:

            status = "RECOVERY_PENDING"

            result = (
                "Kubernetes deployment is ready, "
                "but fresh Prometheus CPU metrics "
                "for the current pods are not "
                "available yet."
            )

            confidence = "HIGH"

            findings.append(
                "Fresh CPU metrics were not available."
            )

            return store_verification(
                state=state,
                status=status,
                result=result,
                confidence=confidence,
                remediation_mode=remediation_mode,
                remediation_executed=remediation_executed,
                remediation_status=remediation_status,
                target_pod=target_pod,
                target_service=target_service,
                deployment_name=deployment_name,
                replicas_before=replicas_before,
                replicas_after=replicas_after,
                findings=findings,
                current_pods=current_pods,
                cpu_data=cpu_data,
                memory_data=memory_data,
            )

        # ====================================================
        # RESOURCE RECOVERY
        # ====================================================

        resource_recovered, resource_findings = (
            check_resource_recovery(

                incidents=incidents,

                cpu_data=cpu_data,

                memory_data=memory_data,

                current_pods=current_pods,

            )
        )

        findings.extend(
            resource_findings
        )

        # ====================================================
        # FINAL VERIFICATION DECISION
        # ====================================================

        if (
            replica_health
            and resource_recovered
        ):

            status = "RECOVERED"

            result = (
                "Incident recovery was confirmed. "
                "The deployment is ready and current "
                "Prometheus resource metrics are below "
                "the relevant critical thresholds."
            )

            confidence = "HIGH"

        else:

            status = "NOT_RECOVERED"

            result = (
                "The incident condition could not "
                "be confirmed as recovered."
            )

            confidence = "HIGH"

        state = store_verification(

            state=state,

            status=status,

            result=result,

            confidence=confidence,

            remediation_mode=remediation_mode,

            remediation_executed=remediation_executed,

            remediation_status=remediation_status,

            target_pod=target_pod,

            target_service=target_service,

            deployment_name=deployment_name,

            replicas_before=replicas_before,

            replicas_after=replicas_after,

            findings=findings,

            current_pods=current_pods,

            cpu_data=cpu_data,

            memory_data=memory_data,

        )

        print(
            f"\nVerification Status: "
            f"{status}"
        )

        print(
            f"Verification Result: "
            f"{result}"
        )

        print(
            f"Confidence: "
            f"{confidence}"
        )

        return state

    # ========================================================
    # VERIFICATION ERROR
    # ========================================================

    except Exception as error:

        status = "RECOVERY_PENDING"

        result = (
            "Verification could not be completed: "
            f"{str(error)}"
        )

        confidence = "LOW"

        findings.append(
            f"Verification error: "
            f"{str(error)}"
        )

        state = store_verification(

            state=state,

            status=status,

            result=result,

            confidence=confidence,

            remediation_mode=remediation_mode,

            remediation_executed=remediation_executed,

            remediation_status=remediation_status,

            target_pod=target_pod,

            target_service=target_service,

            deployment_name=deployment_name,

            replicas_before=replicas_before,

            replicas_after=replicas_after,

            findings=findings,

        )

        print(
            "\nVerification error:"
        )

        print(
            error
        )

        return state