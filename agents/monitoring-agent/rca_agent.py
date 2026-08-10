import requests
import subprocess
import json


# ============================================================
# Configuration
# ============================================================

PROMETHEUS_URL = "http://localhost:9090"

NAMESPACE = "devops-ai"

EXPECTED_SERVICES = [
    "user-service",
    "payment-service",
    "inventory-service"
]


# ============================================================
# Prometheus Query
# ============================================================

def query_prometheus(query):

    response = requests.get(
        f"{PROMETHEUS_URL}/api/v1/query",
        params={"query": query},
        timeout=10
    )

    response.raise_for_status()

    data = response.json()

    if data.get("status") != "success":
        raise RuntimeError(
            f"Prometheus query failed: {data}"
        )

    return data["data"]["result"]


# ============================================================
# Kubernetes Command
# ============================================================

def run_kubectl(command):

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:

        return {
            "success": False,
            "error": result.stderr.strip()
        }

    return {
        "success": True,
        "output": result.stdout.strip()
    }


# ============================================================
# Collect Service Status
# ============================================================

def get_service_status():

    query = (
        'up{namespace="devops-ai",'
        'service=~"user-service|payment-service|inventory-service"}'
    )

    results = query_prometheus(query)

    services = {}

    for item in results:

        metric = item["metric"]

        service = metric.get("service")

        value = item["value"][1]

        if service:

            services[service] = (
                "UP" if value == "1"
                else "DOWN"
            )

    return services


# ============================================================
# Collect CPU Usage
# ============================================================

def get_cpu_usage():

    query = (
        'sum(rate('
        'container_cpu_usage_seconds_total{'
        'namespace="devops-ai",'
        'pod=~"user-service.*|payment-service.*|inventory-service.*"'
        '}[5m])) by (pod)'
    )

    results = query_prometheus(query)

    cpu = {}

    for item in results:

        pod = item["metric"].get("pod")

        if pod:

            cpu[pod] = float(
                item["value"][1]
            )

    return cpu


# ============================================================
# Collect Memory Usage
# ============================================================

def get_memory_usage():

    query = (
        'sum(container_memory_working_set_bytes{'
        'namespace="devops-ai",'
        'pod=~"user-service.*|payment-service.*|inventory-service.*"'
        '}) by (pod)'
    )

    results = query_prometheus(query)

    memory = {}

    for item in results:

        pod = item["metric"].get("pod")

        if pod:

            memory_bytes = float(
                item["value"][1]
            )

            memory[pod] = (
                memory_bytes / (1024 * 1024)
            )

    return memory


# ============================================================
# Collect Kubernetes Pods
# ============================================================

def get_pods():

    command = [
        "kubectl",
        "get",
        "pods",
        "-n",
        NAMESPACE,
        "-o",
        "json"
    ]

    result = run_kubectl(command)

    if not result["success"]:

        return []

    try:

        data = json.loads(
            result["output"]
        )

    except json.JSONDecodeError:

        return []

    pods = []

    for item in data.get("items", []):

        metadata = item.get(
            "metadata",
            {}
        )

        status = item.get(
            "status",
            {}
        )

        name = metadata.get(
            "name",
            "unknown"
        )

        phase = status.get(
            "phase",
            "Unknown"
        )

        restart_count = 0

        for container in status.get(
            "containerStatuses",
            []
        ):

            restart_count += container.get(
                "restartCount",
                0
            )

        pods.append({
            "name": name,
            "phase": phase,
            "restart_count": restart_count
        })

    return pods


# ============================================================
# Collect Kubernetes Events
# ============================================================

def get_kubernetes_events():

    command = [
        "kubectl",
        "get",
        "events",
        "-n",
        NAMESPACE,
        "--sort-by=.lastTimestamp"
    ]

    result = run_kubectl(command)

    if not result["success"]:

        return ""

    return result["output"]


# ============================================================
# Collect Application Logs
# ============================================================

def get_service_logs(service):

    command = [
        "kubectl",
        "logs",
        "-n",
        NAMESPACE,
        "-l",
        f"app={service}",
        "--tail=50"
    ]

    result = run_kubectl(command)

    if not result["success"]:

        return ""

    return result["output"]


# ============================================================
# Find Service Pod
# ============================================================

def find_service_pod(service, pods):

    for pod in pods:

        if pod["name"].startswith(
            service + "-"
        ):

            return pod

    return None


# ============================================================
# Analyse Service Availability
# ============================================================

def analyse_service_failure(
    service,
    status,
    pod
):

    # --------------------------------------------------------
    # Service is DOWN
    # --------------------------------------------------------

    if status == "DOWN":

        if pod is None:

            return {
                "severity": "CRITICAL",
                "root_cause": (
                    f"{service} has no running pod."
                ),
                "evidence": (
                    "Prometheus reports the service as DOWN "
                    "and no corresponding Kubernetes pod "
                    "was found."
                ),
                "recommendation": (
                    f"Check the {service} deployment, "
                    "replica count, EndpointSlice, "
                    "pod scheduling and Kubernetes events."
                )
            }

        if pod["phase"] != "Running":

            return {
                "severity": "CRITICAL",
                "root_cause": (
                    f"{service} pod is not running."
                ),
                "evidence": (
                    f"Pod {pod['name']} is currently in "
                    f"{pod['phase']} state."
                ),
                "recommendation": (
                    "Inspect the pod description, "
                    "Kubernetes events and application logs."
                )
            }

        if pod["restart_count"] > 3:

            return {
                "severity": "CRITICAL",
                "root_cause": (
                    f"{service} is experiencing repeated "
                    "container restarts."
                ),
                "evidence": (
                    f"Pod {pod['name']} has "
                    f"{pod['restart_count']} restarts."
                ),
                "recommendation": (
                    "Inspect application logs and Kubernetes "
                    "events for crash or configuration errors."
                )
            }

        return {
            "severity": "CRITICAL",
            "root_cause": (
                f"{service} is unavailable."
            ),
            "evidence": (
                "Prometheus reports the service as DOWN."
            ),
            "recommendation": (
                "Investigate Kubernetes endpoints, "
                "pod health and application logs."
            )
        }

    # --------------------------------------------------------
    # Service is UP
    # --------------------------------------------------------

    return None


# ============================================================
# Analyse CPU
# ============================================================

def analyse_cpu(cpu_data):

    findings = []

    for pod, cpu in cpu_data.items():

        if cpu >= 0.80:

            findings.append({
                "pod": pod,
                "severity": "CRITICAL",
                "message": (
                    f"{pod} has critically high CPU usage "
                    f"({cpu:.3f} cores)."
                )
            })

        elif cpu >= 0.50:

            findings.append({
                "pod": pod,
                "severity": "WARNING",
                "message": (
                    f"{pod} has elevated CPU usage "
                    f"({cpu:.3f} cores)."
                )
            })

    return findings


# ============================================================
# Analyse Memory
# ============================================================

def analyse_memory(memory_data):

    findings = []

    for pod, memory in memory_data.items():

        if memory >= 200:

            findings.append({
                "pod": pod,
                "severity": "CRITICAL",
                "message": (
                    f"{pod} has critically high memory usage "
                    f"({memory:.2f} MB)."
                )
            })

        elif memory >= 100:

            findings.append({
                "pod": pod,
                "severity": "WARNING",
                "message": (
                    f"{pod} has elevated memory usage "
                    f"({memory:.2f} MB)."
                )
            })

    return findings


# ============================================================
# Analyse Kubernetes Events
# ============================================================

def analyse_events(events):

    findings = []

    if not events:

        return findings

    # IMPORTANT:
    # "Killing" is intentionally NOT included.
    #
    # Kubernetes can generate a Killing event during
    # completely normal operations such as:
    #
    # kubectl scale deployment payment-service --replicas=0
    #
    # Therefore it should not automatically be treated
    # as an infrastructure failure.

    important_keywords = [
        "Failed",
        "BackOff",
        "Error",
        "Unhealthy",
        "FailedMount",
        "FailedScheduling"
    ]

    for line in events.splitlines():

        line_lower = line.lower()

        for keyword in important_keywords:

            if keyword.lower() in line_lower:

                findings.append({
                    "severity": "WARNING",
                    "message": line.strip()
                })

                break

    return findings


# ============================================================
# Analyse Application Logs
# ============================================================

def analyse_logs(logs):

    findings = []

    if not logs:

        return findings

    error_keywords = [
        "error",
        "exception",
        "traceback",
        "failed",
        "fatal"
    ]

    for line in logs.splitlines():

        line_lower = line.lower()

        for keyword in error_keywords:

            if keyword in line_lower:

                findings.append({
                    "severity": "WARNING",
                    "message": line.strip()
                })

                break

    return findings


# ============================================================
# Determine Root Cause
# ============================================================

def determine_root_cause(
    service_findings,
    cpu_findings,
    memory_findings,
    event_findings,
    log_findings
):

    # ========================================================
    # Priority 1 — Service failure
    # ========================================================

    if service_findings:

        primary = service_findings[0]

        return {
            "severity": primary["severity"],
            "root_cause": primary["root_cause"],
            "evidence": primary["evidence"],
            "recommendation": primary["recommendation"]
        }

    # ========================================================
    # Priority 2 — Critical CPU
    # ========================================================

    critical_cpu = [
        finding
        for finding in cpu_findings
        if finding["severity"] == "CRITICAL"
    ]

    if critical_cpu:

        finding = critical_cpu[0]

        return {
            "severity": "CRITICAL",
            "root_cause": (
                "High CPU utilisation detected."
            ),
            "evidence": finding["message"],
            "recommendation": (
                "Investigate workload increase, "
                "CPU limits and application processing."
            )
        }

    # ========================================================
    # Priority 3 — Critical Memory
    # ========================================================

    critical_memory = [
        finding
        for finding in memory_findings
        if finding["severity"] == "CRITICAL"
    ]

    if critical_memory:

        finding = critical_memory[0]

        return {
            "severity": "CRITICAL",
            "root_cause": (
                "High memory utilisation detected."
            ),
            "evidence": finding["message"],
            "recommendation": (
                "Investigate memory usage, memory limits "
                "and possible memory leaks."
            )
        }

    # ========================================================
    # Priority 4 — Kubernetes events
    # ========================================================

    if event_findings:

        finding = event_findings[0]

        return {
            "severity": finding["severity"],
            "root_cause": (
                "A recent Kubernetes event indicates "
                "a possible infrastructure or deployment problem."
            ),
            "evidence": finding["message"],
            "recommendation": (
                "Inspect the affected pod, deployment "
                "and Kubernetes event history."
            )
        }

    # ========================================================
    # Priority 5 — Application logs
    # ========================================================

    if log_findings:

        finding = log_findings[0]

        service = finding.get(
            "service",
            "affected service"
        )

        return {
            "severity": "WARNING",
            "root_cause": (
                f"Application error detected in {service} logs."
            ),
            "evidence": finding["message"],
            "recommendation": (
                "Investigate the application error "
                "and associated request."
            )
        }

    # ========================================================
    # No incident
    # ========================================================

    return {
        "severity": "NORMAL",
        "root_cause": (
            "No significant problem detected."
        ),
        "evidence": (
            "All monitored services are available and "
            "CPU and memory usage are within configured thresholds."
        ),
        "recommendation": (
            "No action required."
        )
    }


# ============================================================
# RCA Pipeline
# ============================================================

def run_rca():

    print("\nCollecting evidence...")

    # --------------------------------------------------------
    # Collect evidence
    # --------------------------------------------------------

    services = get_service_status()

    cpu = get_cpu_usage()

    memory = get_memory_usage()

    pods = get_pods()

    events = get_kubernetes_events()

    logs = {}

    for service in EXPECTED_SERVICES:

        logs[service] = get_service_logs(
            service
        )

    # --------------------------------------------------------
    # Analyse service availability
    # --------------------------------------------------------

    service_findings = []

    for service in EXPECTED_SERVICES:

        # If Prometheus has no result for an expected
        # service, treat it as DOWN.

        status = services.get(
            service,
            "DOWN"
        )

        pod = find_service_pod(
            service,
            pods
        )

        finding = analyse_service_failure(
            service,
            status,
            pod
        )

        if finding:

            service_findings.append(
                finding
            )

    # --------------------------------------------------------
    # Analyse CPU
    # --------------------------------------------------------

    cpu_findings = analyse_cpu(
        cpu
    )

    # --------------------------------------------------------
    # Analyse memory
    # --------------------------------------------------------

    memory_findings = analyse_memory(
        memory
    )

    # --------------------------------------------------------
    # Analyse Kubernetes events
    # --------------------------------------------------------

    event_findings = analyse_events(
        events
    )

    # --------------------------------------------------------
    # Analyse application logs
    # --------------------------------------------------------

    log_findings = []

    for service, service_logs in logs.items():

        findings = analyse_logs(
            service_logs
        )

        for finding in findings:

            finding["service"] = service

            log_findings.append(
                finding
            )

    # --------------------------------------------------------
    # Determine root cause
    # --------------------------------------------------------

    rca = determine_root_cause(
        service_findings,
        cpu_findings,
        memory_findings,
        event_findings,
        log_findings
    )

    return rca


# ============================================================
# Display RCA
# ============================================================

def display_rca(rca):

    print("\n")
    print("=" * 60)
    print("              ROOT CAUSE ANALYSIS")
    print("=" * 60)

    print(
        f"\nSeverity: {rca['severity']}"
    )

    print("\nRoot Cause:")

    print(
        rca["root_cause"]
    )

    print("\nEvidence:")

    print(
        rca["evidence"]
    )

    print("\nRecommended Action:")

    print(
        rca["recommendation"]
    )

    print("\n" + "=" * 60)
    print("             RCA COMPLETED")
    print("=" * 60)


# ============================================================
# Main
# ============================================================

def main():

    print("=" * 60)
    print("             DEVOPS RCA AGENT")
    print("=" * 60)

    # --------------------------------------------------------
    # Check Prometheus
    # --------------------------------------------------------

    try:

        health = requests.get(
            f"{PROMETHEUS_URL}/-/healthy",
            timeout=5
        )

        health.raise_for_status()

        print("\nPrometheus connection: OK")

    except requests.RequestException as error:

        print(
            f"\nPrometheus connection failed: {error}"
        )

        return

    # --------------------------------------------------------
    # Run RCA
    # --------------------------------------------------------

    try:

        rca = run_rca()

        display_rca(
            rca
        )

    except Exception as error:

        print(
            f"\nRCA failed: {error}"
        )


# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":

    main()