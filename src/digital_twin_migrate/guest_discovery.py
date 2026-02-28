"""Guest-level workload discovery engine.

Connects to VMs via SSH (Linux) or WinRM (Windows) and discovers running
databases, web applications, container runtimes, orchestrators, listening
ports, and established connections.

Usage
-----
    discoverer = GuestDiscoverer()
    result = discoverer.discover_all(vm_targets, linux_cred, windows_cred)
"""

from __future__ import annotations

import logging
import re
import socket
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from typing import Any

from .models_workload import (
    ContainerInfo,
    ContainerRuntimeType,
    DatabaseEngine,
    DiscoveredContainerRuntime,
    DiscoveredDatabase,
    DiscoveredOrchestrator,
    DiscoveredWebApp,
    EstablishedConnection,
    ListeningPort,
    OrchestratorType,
    VMWorkloads,
    WebAppRuntime,
    WorkloadDependency,
    WorkloadDiscoveryResult,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Credential containers
# ---------------------------------------------------------------------------

class Credential:
    def __init__(self, username: str, password: str, *, port: int = 0,
                 key_file: str = "", use_sudo: bool = True):
        self.username = username
        self.password = password
        self.port = port
        self.key_file = key_file
        self.use_sudo = use_sudo


class DatabaseCredential:
    """Credentials for direct database server connections."""
    def __init__(self, engine: str, username: str, password: str,
                 *, port: int = 0, host: str = ""):
        self.engine = engine.lower()    # mssql / mysql / postgresql / oracle / mongodb / redis / auto
        self.username = username
        self.password = password
        self.port = port or self._default_port()
        self.host = host                # optional — if empty, use the VM's IP

    def _default_port(self) -> int:
        return {
            "mssql": 1433, "mysql": 3306, "mariadb": 3306,
            "postgresql": 5432, "oracle": 1521,
            "mongodb": 27017, "redis": 6379,
        }.get(self.engine, 0)


# ---------------------------------------------------------------------------
# Remote command runners
# ---------------------------------------------------------------------------

def _run_ssh(ip: str, cred: Credential, command: str, timeout: int = 30) -> str:
    """Execute a command over SSH and return stdout."""
    try:
        import paramiko  # type: ignore
    except ImportError:
        raise RuntimeError("paramiko is required for Linux guest discovery. "
                           "Install with: pip install paramiko")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    port = cred.port or 22
    try:
        connect_kwargs: dict[str, Any] = dict(
            hostname=ip, port=port, username=cred.username,
            password=cred.password, timeout=timeout, allow_agent=False,
            look_for_keys=False, banner_timeout=timeout,
        )
        if cred.key_file:
            connect_kwargs["key_filename"] = cred.key_file
            connect_kwargs.pop("password", None)
        client.connect(**connect_kwargs)
        if cred.use_sudo and cred.username != "root":
            command = f"sudo -n {command} 2>/dev/null || {command}"
        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        return stdout.read().decode("utf-8", errors="replace")
    finally:
        client.close()


def _run_winrm(ip: str, cred: Credential, command: str, ps: bool = True) -> str:
    """Execute a command over WinRM (PowerShell) and return stdout."""
    try:
        import winrm  # type: ignore
    except ImportError:
        raise RuntimeError("pywinrm is required for Windows guest discovery. "
                           "Install with: pip install pywinrm")

    port = cred.port or 5985
    url = f"http://{ip}:{port}/wsman"
    session = winrm.Session(url, auth=(cred.username, cred.password),
                            transport="ntlm")
    if ps:
        result = session.run_ps(command)
    else:
        result = session.run_cmd(command)
    out = result.std_out.decode("utf-8", errors="replace")
    return out


# ===================================================================
#  LINUX PROBES
# ===================================================================

def _probe_linux_ports(ip: str, cred: Credential) -> tuple[list[ListeningPort], list[EstablishedConnection]]:
    """Discover listening ports and established connections on Linux."""
    listening: list[ListeningPort] = []
    established: list[EstablishedConnection] = []

    raw = _run_ssh(ip, cred, "ss -tnlp 2>/dev/null || netstat -tlnp 2>/dev/null")
    for line in raw.splitlines():
        # ss format: LISTEN  0  128  0.0.0.0:3306  0.0.0.0:*  users:(("mysqld",pid=1234,fd=3))
        m = re.search(r'LISTEN\s+\d+\s+\d+\s+(\S+):(\d+)\s+\S+\s*(.*)', line)
        if m:
            addr, port_s, extra = m.group(1), m.group(2), m.group(3)
            proc = ""
            pid = 0
            pm = re.search(r'users:\(\("([^"]+)",pid=(\d+)', extra)
            if pm:
                proc, pid = pm.group(1), int(pm.group(2))
            listening.append(ListeningPort(port=int(port_s), address=addr, process=proc, pid=pid))
            continue
        # netstat format: tcp  0  0  0.0.0.0:3306  0.0.0.0:*  LISTEN  1234/mysqld
        m2 = re.search(r'tcp\S*\s+\d+\s+\d+\s+(\S+):(\d+)\s+\S+\s+LISTEN\s+(\d+)/(\S+)', line)
        if m2:
            addr = m2.group(1)
            port_s = m2.group(2)
            pid = int(m2.group(3))
            proc = m2.group(4)
            listening.append(ListeningPort(port=int(port_s), address=addr, process=proc, pid=pid))

    # Established connections
    raw2 = _run_ssh(ip, cred, "ss -tnp state established 2>/dev/null || netstat -tnp 2>/dev/null | grep ESTABLISHED")
    for line in raw2.splitlines():
        # ss: ESTAB  0  0  10.0.0.5:54321  10.0.0.10:3306  users:(("java",pid=999,fd=5))
        m = re.search(r'ESTAB\s+\d+\s+\d+\s+\S+:(\d+)\s+(\S+):(\d+)\s*(.*)', line)
        if m:
            lport = int(m.group(1))
            rip = m.group(2)
            rport = int(m.group(3))
            proc = ""
            pid = 0
            pm = re.search(r'users:\(\("([^"]+)",pid=(\d+)', m.group(4))
            if pm:
                proc, pid = pm.group(1), int(pm.group(2))
            established.append(EstablishedConnection(
                local_port=lport, remote_ip=rip, remote_port=rport, process=proc, pid=pid))
            continue
        # netstat fallback
        m2 = re.search(r'tcp\S*\s+\d+\s+\d+\s+\S+:(\d+)\s+(\S+):(\d+)\s+ESTABLISHED\s+(\d+)/(\S+)', line)
        if m2:
            established.append(EstablishedConnection(
                local_port=int(m2.group(1)), remote_ip=m2.group(2),
                remote_port=int(m2.group(3)), process=m2.group(5), pid=int(m2.group(4))))

    return listening, established


def _probe_linux_databases(ip: str, cred: Credential, ports: list[ListeningPort]) -> list[DiscoveredDatabase]:
    """Detect database engines running on a Linux VM."""
    dbs: list[DiscoveredDatabase] = []
    port_set = {p.port for p in ports}
    proc_set = {p.process.lower() for p in ports}

    # --- MySQL / MariaDB (3306) ---
    if 3306 in port_set or any(p in proc_set for p in ("mysqld", "mariadbd")):
        ver = _run_ssh(ip, cred, "mysql --version 2>/dev/null || mysqld --version 2>/dev/null").strip()
        version = re.search(r'(\d+\.\d+\.\d+)', ver)
        engine = DatabaseEngine.MARIADB if "mariadb" in ver.lower() else DatabaseEngine.MYSQL
        databases: list[str] = []
        db_list = _run_ssh(ip, cred,
            "mysql -N -e 'SELECT schema_name FROM information_schema.schemata' 2>/dev/null")
        if db_list.strip():
            databases = [d.strip() for d in db_list.strip().splitlines() if d.strip()]
        dbs.append(DiscoveredDatabase(
            engine=engine, port=3306,
            version=version.group(1) if version else "unknown",
            instance_name="default",
            databases=databases,
        ))

    # --- PostgreSQL (5432) ---
    if 5432 in port_set or "postgres" in proc_set:
        ver = _run_ssh(ip, cred, "psql --version 2>/dev/null || postgres --version 2>/dev/null").strip()
        version = re.search(r'(\d+[\.\d]*)', ver)
        databases = []
        db_list = _run_ssh(ip, cred,
            "sudo -u postgres psql -t -c 'SELECT datname FROM pg_database WHERE datistemplate=false' 2>/dev/null")
        if db_list.strip():
            databases = [d.strip() for d in db_list.strip().splitlines() if d.strip()]
        dbs.append(DiscoveredDatabase(
            engine=DatabaseEngine.POSTGRESQL, port=5432,
            version=version.group(1) if version else "unknown",
            instance_name="default", databases=databases,
        ))

    # --- MSSQL on Linux (1433) ---
    if 1433 in port_set or "sqlservr" in proc_set:
        ver = _run_ssh(ip, cred,
            "/opt/mssql/bin/sqlservr --version 2>/dev/null || "
            "sqlcmd -Q 'SELECT @@VERSION' -h -1 2>/dev/null | head -1").strip()
        version = re.search(r'(\d+\.\d+[\.\d]*)', ver)
        dbs.append(DiscoveredDatabase(
            engine=DatabaseEngine.MSSQL, port=1433,
            version=version.group(1) if version else "unknown",
            instance_name="MSSQLSERVER",
        ))

    # --- Oracle (1521) ---
    if 1521 in port_set or any("ora_pmon" in p.process for p in ports):
        ver = _run_ssh(ip, cred,
            "cat $ORACLE_HOME/bin/oraversion 2>/dev/null || "
            "su - oracle -c 'sqlplus -V' 2>/dev/null || echo 'unknown' ").strip()
        version = re.search(r'(\d+[\.\d]+)', ver)
        sid_raw = _run_ssh(ip, cred, "ps aux 2>/dev/null | grep ora_pmon | grep -v grep")
        sid = ""
        sm = re.search(r'ora_pmon_(\S+)', sid_raw)
        if sm:
            sid = sm.group(1)
        dbs.append(DiscoveredDatabase(
            engine=DatabaseEngine.ORACLE, port=1521,
            version=version.group(1) if version else "unknown",
            instance_name=sid or "ORCL",
        ))

    # --- MongoDB (27017) ---
    if 27017 in port_set or "mongod" in proc_set:
        ver = _run_ssh(ip, cred, "mongod --version 2>/dev/null").strip()
        version = re.search(r'v(\d+[\.\d]+)', ver)
        dbs.append(DiscoveredDatabase(
            engine=DatabaseEngine.MONGODB, port=27017,
            version=version.group(1) if version else "unknown",
            instance_name="default",
        ))

    # --- Redis (6379) ---
    if 6379 in port_set or "redis-server" in proc_set:
        ver = _run_ssh(ip, cred, "redis-server --version 2>/dev/null").strip()
        version = re.search(r'v=(\d+[\.\d]+)', ver)
        dbs.append(DiscoveredDatabase(
            engine=DatabaseEngine.REDIS, port=6379,
            version=version.group(1) if version else "unknown",
            instance_name="default",
        ))

    return dbs


def _probe_linux_webapps(ip: str, cred: Credential, ports: list[ListeningPort]) -> list[DiscoveredWebApp]:
    """Detect web application runtimes on Linux."""
    apps: list[DiscoveredWebApp] = []
    proc_set = {p.process.lower(): p for p in ports}

    processes_raw = _run_ssh(ip, cred, "ps aux 2>/dev/null")
    lines = processes_raw.splitlines()

    # --- .NET Core / .NET 5+ ---
    dotnet_procs = [l for l in lines if "dotnet" in l.lower() and "grep" not in l]
    if dotnet_procs or "dotnet" in proc_set:
        ver = _run_ssh(ip, cred, "dotnet --list-runtimes 2>/dev/null").strip()
        version = re.search(r'Microsoft\.AspNetCore\.App (\S+)', ver)
        if not version:
            version = re.search(r'Microsoft\.NETCore\.App (\S+)', ver)
        for pp in ports:
            if pp.process.lower() == "dotnet" or (pp.port in (5000, 5001, 80, 443) and "dotnet" in pp.process.lower()):
                apps.append(DiscoveredWebApp(
                    runtime=WebAppRuntime.DOTNET_CORE,
                    runtime_version=version.group(1) if version else "unknown",
                    framework="ASP.NET Core",
                    port=pp.port, process_name=pp.process, pid=pp.pid,
                ))
                break
        else:
            if dotnet_procs:
                apps.append(DiscoveredWebApp(
                    runtime=WebAppRuntime.DOTNET_CORE,
                    runtime_version=version.group(1) if version else "unknown",
                    framework="ASP.NET Core",
                ))

    # --- Java (Tomcat / JBoss / WildFly / Spring Boot) ---
    java_procs = [l for l in lines if re.search(r'\bjava\b', l) and "grep" not in l]
    if java_procs:
        ver = _run_ssh(ip, cred, "java -version 2>&1 | head -1").strip()
        version = re.search(r'"(\d+[\.\d_]+)"', ver) or re.search(r'(\d+[\.\d]+)', ver)
        framework = "Java"
        for jp in java_procs:
            jl = jp.lower()
            if "tomcat" in jl or "catalina" in jl:
                framework = "Apache Tomcat"
            elif "jboss" in jl or "wildfly" in jl:
                framework = "JBoss / WildFly"
            elif "spring" in jl:
                framework = "Spring Boot"
            elif "jetty" in jl:
                framework = "Jetty"
        port = 8080
        for pp in ports:
            if pp.process.lower() == "java" or "java" in pp.process.lower():
                port = pp.port
                break
        apps.append(DiscoveredWebApp(
            runtime=WebAppRuntime.JAVA,
            runtime_version=version.group(1) if version else "unknown",
            framework=framework, port=port,
        ))

    # --- Node.js ---
    node_procs = [l for l in lines if re.search(r'\bnode\b', l) and "grep" not in l]
    if node_procs or "node" in proc_set:
        ver = _run_ssh(ip, cred, "node --version 2>/dev/null").strip()
        port = 3000
        for pp in ports:
            if pp.process.lower() == "node":
                port = pp.port
                break
        framework = "Node.js"
        for nl in node_procs:
            if "express" in nl.lower():
                framework = "Express.js"
            elif "next" in nl.lower():
                framework = "Next.js"
        apps.append(DiscoveredWebApp(
            runtime=WebAppRuntime.NODEJS,
            runtime_version=ver.replace("v", "") or "unknown",
            framework=framework, port=port,
        ))

    # --- Python (Django / Flask / FastAPI / gunicorn / uvicorn) ---
    py_web = [l for l in lines if any(k in l.lower() for k in ("gunicorn", "uvicorn", "uwsgi", "django", "flask")) and "grep" not in l]
    if py_web:
        ver = _run_ssh(ip, cred, "python3 --version 2>/dev/null || python --version 2>/dev/null").strip()
        version = re.search(r'(\d+[\.\d]+)', ver)
        framework = "Python"
        for pl in py_web:
            pl_l = pl.lower()
            if "django" in pl_l:
                framework = "Django"
            elif "flask" in pl_l:
                framework = "Flask"
            elif "fastapi" in pl_l or "uvicorn" in pl_l:
                framework = "FastAPI"
        port = 8000
        for pp in ports:
            if pp.process.lower() in ("gunicorn", "uvicorn", "uwsgi", "python", "python3"):
                port = pp.port
                break
        apps.append(DiscoveredWebApp(
            runtime=WebAppRuntime.PYTHON,
            runtime_version=version.group(1) if version else "unknown",
            framework=framework, port=port,
        ))

    # --- PHP (PHP-FPM / Apache mod_php) ---
    php_procs = [l for l in lines if "php" in l.lower() and "grep" not in l]
    if php_procs or any("php" in p.process.lower() for p in ports):
        ver = _run_ssh(ip, cred, "php --version 2>/dev/null | head -1").strip()
        version = re.search(r'(\d+[\.\d]+)', ver)
        framework = "PHP"
        for pl in php_procs:
            if "laravel" in pl.lower():
                framework = "Laravel"
            elif "wordpress" in pl.lower():
                framework = "WordPress"
        apps.append(DiscoveredWebApp(
            runtime=WebAppRuntime.PHP,
            runtime_version=version.group(1) if version else "unknown",
            framework=framework, port=80,
        ))

    # --- Nginx / Apache / httpd (as reverse proxy / web server) ---
    for pp in ports:
        if pp.process.lower() in ("nginx", "apache2", "httpd") and pp.port in (80, 443, 8080):
            # These are web servers, not specific apps — note if no app already found
            if not any(a.port == pp.port for a in apps):
                apps.append(DiscoveredWebApp(
                    runtime=WebAppRuntime.UNKNOWN,
                    framework=pp.process.capitalize() + " web server",
                    port=pp.port, process_name=pp.process, pid=pp.pid,
                ))

    return apps


def _probe_linux_containers(ip: str, cred: Credential) -> list[DiscoveredContainerRuntime]:
    """Detect container runtimes and running containers on Linux."""
    runtimes: list[DiscoveredContainerRuntime] = []

    # --- Docker ---
    docker_ver = _run_ssh(ip, cred, "docker version --format '{{.Server.Version}}' 2>/dev/null").strip()
    if docker_ver and "error" not in docker_ver.lower() and "command not found" not in docker_ver.lower():
        containers: list[ContainerInfo] = []
        ps_raw = _run_ssh(ip, cred,
            "docker ps --format '{{.ID}}|{{.Names}}|{{.Image}}|{{.Status}}|{{.Ports}}' 2>/dev/null")
        total = 0
        running = 0
        for line in ps_raw.strip().splitlines():
            parts = line.split("|")
            if len(parts) >= 4:
                containers.append(ContainerInfo(
                    container_id=parts[0][:12],
                    name=parts[1],
                    image=parts[2],
                    status=parts[3],
                    ports=parts[4].split(",") if len(parts) > 4 and parts[4] else [],
                ))
                running += 1
        # Count all containers
        all_raw = _run_ssh(ip, cred, "docker ps -aq 2>/dev/null | wc -l").strip()
        try:
            total = int(all_raw)
        except ValueError:
            total = running
        runtimes.append(DiscoveredContainerRuntime(
            runtime=ContainerRuntimeType.DOCKER, version=docker_ver,
            containers=containers, total_containers=total, running_containers=running,
        ))

    # --- Podman ---
    podman_ver = _run_ssh(ip, cred, "podman version --format '{{.Version}}' 2>/dev/null").strip()
    if podman_ver and "error" not in podman_ver.lower() and "command not found" not in podman_ver.lower():
        containers = []
        ps_raw = _run_ssh(ip, cred,
            "podman ps --format '{{.ID}}|{{.Names}}|{{.Image}}|{{.Status}}|{{.Ports}}' 2>/dev/null")
        running = 0
        for line in ps_raw.strip().splitlines():
            parts = line.split("|")
            if len(parts) >= 4:
                containers.append(ContainerInfo(
                    container_id=parts[0][:12], name=parts[1],
                    image=parts[2], status=parts[3],
                ))
                running += 1
        runtimes.append(DiscoveredContainerRuntime(
            runtime=ContainerRuntimeType.PODMAN, version=podman_ver,
            containers=containers, running_containers=running, total_containers=running,
        ))

    # --- containerd (via ctr) ---
    ctr_ver = _run_ssh(ip, cred, "ctr version 2>/dev/null | grep 'Version' | head -1").strip()
    if ctr_ver and "command not found" not in ctr_ver.lower():
        version = re.search(r'(\d+[\.\d]+)', ctr_ver)
        runtimes.append(DiscoveredContainerRuntime(
            runtime=ContainerRuntimeType.CONTAINERD,
            version=version.group(1) if version else "unknown",
        ))

    return runtimes


def _probe_linux_orchestrators(ip: str, cred: Credential) -> list[DiscoveredOrchestrator]:
    """Detect container orchestrators on Linux."""
    orchs: list[DiscoveredOrchestrator] = []

    # --- Kubernetes ---
    kubelet_ver = _run_ssh(ip, cred, "kubelet --version 2>/dev/null").strip()
    if kubelet_ver and "command not found" not in kubelet_ver.lower():
        version = re.search(r'v(\d+[\.\d]+)', kubelet_ver)
        role = "worker"
        # Check if API server is running (control plane indicator)
        api_check = _run_ssh(ip, cred, "ps aux 2>/dev/null | grep kube-apiserver | grep -v grep")
        if api_check.strip():
            role = "control-plane"
        # Try kubectl info
        nodes = 0
        pods = 0
        ns = 0
        cluster_name = ""
        if role == "control-plane":
            ctx = _run_ssh(ip, cred, "kubectl config current-context 2>/dev/null").strip()
            if ctx:
                cluster_name = ctx
            node_count = _run_ssh(ip, cred, "kubectl get nodes --no-headers 2>/dev/null | wc -l").strip()
            try:
                nodes = int(node_count)
            except ValueError:
                pass
            pod_count = _run_ssh(ip, cred,
                "kubectl get pods --all-namespaces --no-headers 2>/dev/null | wc -l").strip()
            try:
                pods = int(pod_count)
            except ValueError:
                pass
            ns_count = _run_ssh(ip, cred, "kubectl get namespaces --no-headers 2>/dev/null | wc -l").strip()
            try:
                ns = int(ns_count)
            except ValueError:
                pass
        orchs.append(DiscoveredOrchestrator(
            type=OrchestratorType.KUBERNETES,
            version=version.group(1) if version else "unknown",
            role=role, cluster_name=cluster_name,
            node_count=nodes, pod_count=pods, namespace_count=ns,
        ))

    # --- Docker Swarm ---
    swarm_check = _run_ssh(ip, cred, "docker info --format '{{.Swarm.LocalNodeState}}' 2>/dev/null").strip()
    if swarm_check == "active":
        role = "worker"
        mgr = _run_ssh(ip, cred, "docker info --format '{{.Swarm.ControlAvailable}}' 2>/dev/null").strip()
        if mgr.lower() == "true":
            role = "manager"
        nodes = 0
        node_raw = _run_ssh(ip, cred, "docker node ls --format '{{.ID}}' 2>/dev/null | wc -l").strip()
        try:
            nodes = int(node_raw)
        except ValueError:
            pass
        orchs.append(DiscoveredOrchestrator(
            type=OrchestratorType.DOCKER_SWARM, role=role, node_count=nodes,
        ))

    return orchs


# ===================================================================
#  WINDOWS PROBES
# ===================================================================

def _probe_win_ports(ip: str, cred: Credential) -> tuple[list[ListeningPort], list[EstablishedConnection]]:
    """Discover listening ports and connections on Windows via WinRM."""
    listening: list[ListeningPort] = []
    established: list[EstablishedConnection] = []

    raw = _run_winrm(ip, cred,
        "Get-NetTCPConnection -State Listen | Select-Object LocalPort,OwningProcess "
        "| Sort-Object LocalPort -Unique | ConvertTo-Csv -NoTypeInformation")
    for line in raw.strip().splitlines()[1:]:  # skip header
        parts = [p.strip('"') for p in line.split(",")]
        if len(parts) >= 2:
            try:
                port = int(parts[0])
                pid = int(parts[1])
            except ValueError:
                continue
            listening.append(ListeningPort(port=port, pid=pid))

    # Resolve process names
    if listening:
        pids = ",".join(str(p.pid) for p in listening if p.pid)
        proc_raw = _run_winrm(ip, cred,
            f"Get-Process -Id {pids} -ErrorAction SilentlyContinue "
            "| Select-Object Id,ProcessName | ConvertTo-Csv -NoTypeInformation")
        pid_name: dict[int, str] = {}
        for line in proc_raw.strip().splitlines()[1:]:
            parts = [p.strip('"') for p in line.split(",")]
            if len(parts) >= 2:
                try:
                    pid_name[int(parts[0])] = parts[1]
                except ValueError:
                    pass
        for p in listening:
            p.process = pid_name.get(p.pid, "")

    # Established outbound
    raw2 = _run_winrm(ip, cred,
        "Get-NetTCPConnection -State Established | "
        "Select-Object LocalPort,RemoteAddress,RemotePort,OwningProcess "
        "| ConvertTo-Csv -NoTypeInformation")
    for line in raw2.strip().splitlines()[1:]:
        parts = [p.strip('"') for p in line.split(",")]
        if len(parts) >= 4:
            try:
                established.append(EstablishedConnection(
                    local_port=int(parts[0]), remote_ip=parts[1],
                    remote_port=int(parts[2]), pid=int(parts[3]),
                ))
            except ValueError:
                pass

    return listening, established


def _probe_win_databases(ip: str, cred: Credential, ports: list[ListeningPort]) -> list[DiscoveredDatabase]:
    """Detect database engines on Windows."""
    dbs: list[DiscoveredDatabase] = []
    port_set = {p.port for p in ports}
    proc_set = {p.process.lower() for p in ports}

    # --- MSSQL ---
    sql_svc = _run_winrm(ip, cred,
        "Get-Service -Name 'MSSQL*' -ErrorAction SilentlyContinue "
        "| Where-Object {$_.Status -eq 'Running'} "
        "| Select-Object Name,DisplayName | ConvertTo-Csv -NoTypeInformation")
    if sql_svc.strip() and len(sql_svc.strip().splitlines()) > 1:
        ver = _run_winrm(ip, cred,
            "try { Invoke-Sqlcmd -Query 'SELECT @@VERSION' -ErrorAction Stop "
            "| Select-Object -ExpandProperty Column1 } catch { 'unknown' }")
        version = re.search(r'(\d+\.\d+[\.\d]*)', ver)
        # Get database list
        databases: list[str] = []
        db_raw = _run_winrm(ip, cred,
            "try { Invoke-Sqlcmd -Query 'SELECT name FROM sys.databases' -ErrorAction Stop "
            "| Select-Object -ExpandProperty name } catch {}")
        if db_raw.strip():
            databases = [d.strip() for d in db_raw.strip().splitlines() if d.strip()]
        for svc_line in sql_svc.strip().splitlines()[1:]:
            parts = [p.strip('"') for p in svc_line.split(",")]
            inst_name = parts[0] if parts else "MSSQLSERVER"
            edition_raw = _run_winrm(ip, cred,
                "try { Invoke-Sqlcmd -Query 'SELECT SERVERPROPERTY(''Edition'')' -ErrorAction Stop "
                "| Select-Object -ExpandProperty Column1 } catch { '' }")
            dbs.append(DiscoveredDatabase(
                engine=DatabaseEngine.MSSQL, port=1433,
                version=version.group(1) if version else "unknown",
                instance_name=inst_name, databases=databases,
                edition=edition_raw.strip(),
            ))

    # --- MySQL on Windows ---
    if 3306 in port_set or "mysqld" in proc_set:
        ver = _run_winrm(ip, cred, "mysql --version 2>&1", ps=False)
        version = re.search(r'(\d+\.\d+[\.\d]*)', ver)
        dbs.append(DiscoveredDatabase(
            engine=DatabaseEngine.MYSQL, port=3306,
            version=version.group(1) if version else "unknown",
            instance_name="default",
        ))

    # --- PostgreSQL on Windows ---
    if 5432 in port_set or "postgres" in proc_set:
        ver = _run_winrm(ip, cred, "psql --version 2>&1", ps=False)
        version = re.search(r'(\d+[\.\d]*)', ver)
        dbs.append(DiscoveredDatabase(
            engine=DatabaseEngine.POSTGRESQL, port=5432,
            version=version.group(1) if version else "unknown",
            instance_name="default",
        ))

    # --- Oracle on Windows ---
    oracle_svc = _run_winrm(ip, cred,
        "Get-Service -Name 'OracleService*' -ErrorAction SilentlyContinue "
        "| Where-Object {$_.Status -eq 'Running'} | Select-Object Name "
        "| ConvertTo-Csv -NoTypeInformation")
    if oracle_svc.strip() and len(oracle_svc.strip().splitlines()) > 1:
        dbs.append(DiscoveredDatabase(
            engine=DatabaseEngine.ORACLE, port=1521,
            version="unknown", instance_name="ORCL",
        ))

    return dbs


def _probe_win_webapps(ip: str, cred: Credential, ports: list[ListeningPort]) -> list[DiscoveredWebApp]:
    """Detect web app runtimes on Windows."""
    apps: list[DiscoveredWebApp] = []

    # --- IIS (.NET Framework / .NET Core hosted) ---
    iis_raw = _run_winrm(ip, cred,
        "try { Import-Module WebAdministration -ErrorAction Stop; "
        "Get-Website | Select-Object Name,State,PhysicalPath,"
        "@{N='Bindings';E={$_.bindings.Collection.bindingInformation -join ';'}} "
        "| ConvertTo-Csv -NoTypeInformation } catch { '' }")
    if iis_raw.strip() and len(iis_raw.strip().splitlines()) > 1:
        for line in iis_raw.strip().splitlines()[1:]:
            parts = [p.strip('"') for p in line.split(",")]
            if len(parts) >= 3:
                site_name = parts[0]
                state = parts[1]
                phys = parts[2] if len(parts) > 2 else ""
                binding = parts[3] if len(parts) > 3 else ""
                # Determine if .NET Framework or .NET Core
                runtime = WebAppRuntime.DOTNET_FRAMEWORK
                framework = "ASP.NET (IIS)"
                # Check for web.config with aspNetCore module
                check = _run_winrm(ip, cred,
                    f"if (Test-Path '{phys}\\web.config') {{ "
                    f"Select-String -Path '{phys}\\web.config' -Pattern 'aspNetCore' -Quiet }}")
                if "True" in check:
                    runtime = WebAppRuntime.DOTNET_CORE
                    framework = "ASP.NET Core (IIS)"
                apps.append(DiscoveredWebApp(
                    runtime=runtime, framework=framework,
                    app_name=site_name, port=80,
                    binding=binding, status=state.lower(),
                ))

    # --- .NET Core Kestrel (standalone) ---
    dotnet_procs = _run_winrm(ip, cred,
        "Get-Process -Name dotnet -ErrorAction SilentlyContinue "
        "| Select-Object Id,ProcessName | ConvertTo-Csv -NoTypeInformation")
    if dotnet_procs.strip() and len(dotnet_procs.strip().splitlines()) > 1:
        ver = _run_winrm(ip, cred, "dotnet --list-runtimes 2>&1")
        version = re.search(r'Microsoft\.AspNetCore\.App (\S+)', ver)
        if not any(a.runtime == WebAppRuntime.DOTNET_CORE for a in apps):
            apps.append(DiscoveredWebApp(
                runtime=WebAppRuntime.DOTNET_CORE,
                runtime_version=version.group(1) if version else "unknown",
                framework="ASP.NET Core (Kestrel)",
                port=5000, process_name="dotnet",
            ))

    # --- Java on Windows ---
    java_procs = _run_winrm(ip, cred,
        "Get-Process -Name java -ErrorAction SilentlyContinue "
        "| Select-Object Id | ConvertTo-Csv -NoTypeInformation")
    if java_procs.strip() and len(java_procs.strip().splitlines()) > 1:
        ver = _run_winrm(ip, cred, "java -version 2>&1 | Select-Object -First 1")
        version = re.search(r'"(\d+[\.\d_]+)"', ver) or re.search(r'(\d+[\.\d]+)', ver)
        apps.append(DiscoveredWebApp(
            runtime=WebAppRuntime.JAVA,
            runtime_version=version.group(1) if version else "unknown",
            framework="Java", port=8080,
        ))

    # --- Node.js on Windows ---
    node_procs = _run_winrm(ip, cred,
        "Get-Process -Name node -ErrorAction SilentlyContinue "
        "| Select-Object Id | ConvertTo-Csv -NoTypeInformation")
    if node_procs.strip() and len(node_procs.strip().splitlines()) > 1:
        ver = _run_winrm(ip, cred, "node --version 2>&1")
        apps.append(DiscoveredWebApp(
            runtime=WebAppRuntime.NODEJS,
            runtime_version=ver.strip().replace("v", "") or "unknown",
            framework="Node.js", port=3000,
        ))

    # --- Docker Desktop on Windows ---
    # (containers handled separately but Docker-hosted web apps noted here)

    return apps


def _probe_win_containers(ip: str, cred: Credential) -> list[DiscoveredContainerRuntime]:
    """Detect container runtimes on Windows."""
    runtimes: list[DiscoveredContainerRuntime] = []

    docker_ver = _run_winrm(ip, cred,
        "docker version --format '{{.Server.Version}}' 2>&1")
    if docker_ver.strip() and "error" not in docker_ver.lower() and "not recognized" not in docker_ver.lower():
        containers: list[ContainerInfo] = []
        running = 0
        ps_raw = _run_winrm(ip, cred,
            "docker ps --format '{{.ID}}|{{.Names}}|{{.Image}}|{{.Status}}|{{.Ports}}' 2>&1")
        for line in ps_raw.strip().splitlines():
            if "|" not in line:
                continue
            parts = line.split("|")
            if len(parts) >= 4:
                containers.append(ContainerInfo(
                    container_id=parts[0][:12], name=parts[1],
                    image=parts[2], status=parts[3],
                ))
                running += 1
        runtimes.append(DiscoveredContainerRuntime(
            runtime=ContainerRuntimeType.DOCKER,
            version=docker_ver.strip(),
            containers=containers, running_containers=running, total_containers=running,
        ))

    return runtimes


def _probe_win_orchestrators(ip: str, cred: Credential) -> list[DiscoveredOrchestrator]:
    """Detect orchestrators on Windows."""
    orchs: list[DiscoveredOrchestrator] = []

    kubectl_ver = _run_winrm(ip, cred, "kubectl version --client --short 2>&1")
    if kubectl_ver.strip() and "not recognized" not in kubectl_ver.lower():
        version = re.search(r'v(\d+[\.\d]+)', kubectl_ver)
        orchs.append(DiscoveredOrchestrator(
            type=OrchestratorType.KUBERNETES,
            version=version.group(1) if version else "unknown",
            role="client",
        ))

    return orchs


# ===================================================================
#  DIRECT DATABASE PROBING (via Python DB drivers)
# ===================================================================

def _deep_probe_mysql(host: str, db_cred: DatabaseCredential,
                      existing: DiscoveredDatabase | None = None) -> DiscoveredDatabase:
    """Connect directly to MySQL/MariaDB and discover databases, tables, sizes."""
    port = db_cred.port or 3306
    db = existing or DiscoveredDatabase(engine=DatabaseEngine.MYSQL, port=port, host=host)
    db.host = host
    db.discovery_method = "direct_connect"
    try:
        import pymysql  # type: ignore
    except ImportError:
        try:
            import mysql.connector as pymysql  # type: ignore
        except ImportError:
            db.connection_error = "pymysql or mysql-connector-python not installed"
            logger.warning("MySQL driver not available for deep probe on %s", host)
            return db

    try:
        conn = pymysql.connect(host=host, port=port, user=db_cred.username,
                               password=db_cred.password, connect_timeout=10)
        cur = conn.cursor()

        # Version
        cur.execute("SELECT VERSION()")
        row = cur.fetchone()
        if row:
            db.version = str(row[0])
            if "mariadb" in db.version.lower():
                db.engine = DatabaseEngine.MARIADB

        # Databases
        cur.execute("SELECT SCHEMA_NAME FROM information_schema.SCHEMATA "
                    "WHERE SCHEMA_NAME NOT IN ('information_schema','performance_schema','mysql','sys')")
        db.databases = [r[0] for r in cur.fetchall()]

        # Table count
        cur.execute("SELECT COUNT(*) FROM information_schema.TABLES "
                    "WHERE TABLE_SCHEMA NOT IN ('information_schema','performance_schema','mysql','sys')")
        db.table_count = cur.fetchone()[0]

        # Schema count
        db.schema_count = len(db.databases)

        # Total size in GB
        cur.execute("SELECT ROUND(SUM(data_length + index_length) / 1073741824, 2) "
                    "FROM information_schema.TABLES")
        row = cur.fetchone()
        db.total_size_gb = float(row[0]) if row and row[0] else 0.0
        db.size_mb = db.total_size_gb * 1024

        # Max connections
        cur.execute("SHOW VARIABLES LIKE 'max_connections'")
        row = cur.fetchone()
        if row:
            db.max_connections = int(row[1])

        # Active connections
        cur.execute("SELECT COUNT(*) FROM information_schema.PROCESSLIST")
        db.active_connections = cur.fetchone()[0]

        # Users
        try:
            cur.execute("SELECT DISTINCT User FROM mysql.user WHERE User != ''")
            db.users = [r[0] for r in cur.fetchall()]
        except Exception:
            pass

        # Edition
        try:
            cur.execute("SHOW VARIABLES LIKE 'version_comment'")
            row = cur.fetchone()
            if row:
                db.edition = str(row[1])
        except Exception:
            pass

        db.instance_name = db.instance_name or "default"
        db.status = "running"
        db.connection_error = ""
        cur.close()
        conn.close()
        logger.info("Deep MySQL probe on %s:%d — %d databases, %.2f GB",
                     host, port, len(db.databases), db.total_size_gb)
    except Exception as exc:
        db.connection_error = str(exc)
        logger.warning("MySQL deep probe failed on %s:%d — %s", host, port, exc)
    return db


def _deep_probe_postgresql(host: str, db_cred: DatabaseCredential,
                           existing: DiscoveredDatabase | None = None) -> DiscoveredDatabase:
    """Connect directly to PostgreSQL and discover databases, tables, sizes."""
    port = db_cred.port or 5432
    db = existing or DiscoveredDatabase(engine=DatabaseEngine.POSTGRESQL, port=port, host=host)
    db.host = host
    db.discovery_method = "direct_connect"
    try:
        import psycopg2  # type: ignore
    except ImportError:
        db.connection_error = "psycopg2 not installed"
        logger.warning("psycopg2 not available for deep probe on %s", host)
        return db

    try:
        conn = psycopg2.connect(host=host, port=port, user=db_cred.username,
                                password=db_cred.password, dbname="postgres",
                                connect_timeout=10)
        conn.autocommit = True
        cur = conn.cursor()

        # Version
        cur.execute("SELECT version()")
        row = cur.fetchone()
        if row:
            m = re.search(r'PostgreSQL (\d+[\.\d]*)', str(row[0]))
            if m:
                db.version = m.group(1)

        # Databases
        cur.execute("SELECT datname FROM pg_database WHERE datistemplate = false")
        db.databases = [r[0] for r in cur.fetchall()]

        # Schema count (across all user DBs, from pg_namespace of current db)
        cur.execute("SELECT COUNT(*) FROM pg_namespace WHERE nspname NOT LIKE 'pg_%' "
                    "AND nspname != 'information_schema'")
        db.schema_count = cur.fetchone()[0]

        # Table count (current db)
        cur.execute("SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema NOT IN ('pg_catalog','information_schema')")
        db.table_count = cur.fetchone()[0]

        # Total size in GB
        cur.execute("SELECT ROUND(SUM(pg_database_size(datname))::numeric / 1073741824, 2) "
                    "FROM pg_database WHERE datistemplate = false")
        row = cur.fetchone()
        db.total_size_gb = float(row[0]) if row and row[0] else 0.0
        db.size_mb = db.total_size_gb * 1024

        # Max connections
        cur.execute("SHOW max_connections")
        row = cur.fetchone()
        if row:
            db.max_connections = int(row[0])

        # Active connections
        cur.execute("SELECT COUNT(*) FROM pg_stat_activity")
        db.active_connections = cur.fetchone()[0]

        # Users
        cur.execute("SELECT usename FROM pg_user")
        db.users = [r[0] for r in cur.fetchall()]

        # Edition
        cur.execute("SELECT version()")
        row = cur.fetchone()
        if row:
            db.edition = str(row[0]).split(",")[0] if row[0] else ""

        db.instance_name = db.instance_name or "default"
        db.status = "running"
        db.connection_error = ""
        cur.close()
        conn.close()
        logger.info("Deep PostgreSQL probe on %s:%d — %d databases, %.2f GB",
                     host, port, len(db.databases), db.total_size_gb)
    except Exception as exc:
        db.connection_error = str(exc)
        logger.warning("PostgreSQL deep probe failed on %s:%d — %s", host, port, exc)
    return db


def _deep_probe_mssql(host: str, db_cred: DatabaseCredential,
                      existing: DiscoveredDatabase | None = None) -> DiscoveredDatabase:
    """Connect directly to SQL Server and discover databases, tables, sizes."""
    port = db_cred.port or 1433
    db = existing or DiscoveredDatabase(engine=DatabaseEngine.MSSQL, port=port, host=host)
    db.host = host
    db.discovery_method = "direct_connect"
    try:
        import pymssql  # type: ignore
    except ImportError:
        db.connection_error = "pymssql not installed"
        logger.warning("pymssql not available for deep probe on %s", host)
        return db

    try:
        conn = pymssql.connect(server=host, port=str(port), user=db_cred.username,
                               password=db_cred.password, login_timeout=10)
        cur = conn.cursor()

        # Version & Edition
        cur.execute("SELECT @@VERSION")
        row = cur.fetchone()
        if row:
            ver_str = str(row[0])
            m = re.search(r'(\d+\.\d+[\.\d]*)', ver_str)
            if m:
                db.version = m.group(1)
            # Extract edition
            m2 = re.search(r'(Enterprise|Standard|Developer|Express|Web)', ver_str)
            if m2:
                db.edition = m2.group(1)

        # Databases
        cur.execute("SELECT name FROM sys.databases WHERE database_id > 4")
        db.databases = [r[0] for r in cur.fetchall()]

        # Table count
        cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_type = 'BASE TABLE'")
        db.table_count = cur.fetchone()[0]

        # Schema count
        cur.execute("SELECT COUNT(DISTINCT table_schema) FROM information_schema.tables")
        db.schema_count = cur.fetchone()[0]

        # Total size in GB
        cur.execute("SELECT ROUND(SUM(CAST(size AS BIGINT)) * 8.0 / 1048576, 2) "
                    "FROM sys.master_files")
        row = cur.fetchone()
        db.total_size_gb = float(row[0]) if row and row[0] else 0.0
        db.size_mb = db.total_size_gb * 1024

        # Max connections (SQL Server default is 32767)
        cur.execute("SELECT @@MAX_CONNECTIONS")
        row = cur.fetchone()
        if row:
            db.max_connections = int(row[0])

        # Active connections
        cur.execute("SELECT COUNT(*) FROM sys.dm_exec_sessions WHERE is_user_process = 1")
        db.active_connections = cur.fetchone()[0]

        # Users
        cur.execute("SELECT name FROM sys.server_principals WHERE type IN ('S','U') "
                    "AND name NOT LIKE '##%' AND name != 'sa'")
        db.users = [r[0] for r in cur.fetchall()]

        db.instance_name = db.instance_name or "MSSQLSERVER"
        db.status = "running"
        db.connection_error = ""
        cur.close()
        conn.close()
        logger.info("Deep MSSQL probe on %s:%d — %d databases, %.2f GB",
                     host, port, len(db.databases), db.total_size_gb)
    except Exception as exc:
        db.connection_error = str(exc)
        logger.warning("MSSQL deep probe failed on %s:%d — %s", host, port, exc)
    return db


def _deep_probe_mongodb(host: str, db_cred: DatabaseCredential,
                        existing: DiscoveredDatabase | None = None) -> DiscoveredDatabase:
    """Connect directly to MongoDB and discover databases, collections, sizes."""
    port = db_cred.port or 27017
    db = existing or DiscoveredDatabase(engine=DatabaseEngine.MONGODB, port=port, host=host)
    db.host = host
    db.discovery_method = "direct_connect"
    try:
        import pymongo  # type: ignore
    except ImportError:
        db.connection_error = "pymongo not installed"
        logger.warning("pymongo not available for deep probe on %s", host)
        return db

    try:
        client = pymongo.MongoClient(
            host=host, port=port,
            username=db_cred.username or None,
            password=db_cred.password or None,
            serverSelectionTimeoutMS=10000, connectTimeoutMS=10000,
        )
        # Force connection
        server_info = client.server_info()
        db.version = server_info.get("version", "unknown")

        # Databases
        db_names = [n for n in client.list_database_names()
                    if n not in ("admin", "config", "local")]
        db.databases = db_names

        # Collection (table) count
        total_collections = 0
        total_size = 0
        for db_name in db_names:
            d = client[db_name]
            total_collections += len(d.list_collection_names())
            stats = d.command("dbStats")
            total_size += stats.get("dataSize", 0) + stats.get("indexSize", 0)
        db.table_count = total_collections
        db.schema_count = len(db_names)
        db.total_size_gb = round(total_size / 1073741824, 2)
        db.size_mb = db.total_size_gb * 1024

        # Users
        try:
            admin_db = client["admin"]
            users_info = admin_db.command("usersInfo")
            db.users = [u["user"] for u in users_info.get("users", [])]
        except Exception:
            pass

        # Active connections
        try:
            status = client.admin.command("serverStatus")
            conns = status.get("connections", {})
            db.active_connections = conns.get("current", 0)
            db.max_connections = conns.get("available", 0) + conns.get("current", 0)
        except Exception:
            pass

        db.instance_name = db.instance_name or "default"
        db.status = "running"
        db.connection_error = ""
        client.close()
        logger.info("Deep MongoDB probe on %s:%d — %d databases, %.2f GB",
                     host, port, len(db.databases), db.total_size_gb)
    except Exception as exc:
        db.connection_error = str(exc)
        logger.warning("MongoDB deep probe failed on %s:%d — %s", host, port, exc)
    return db


def _deep_probe_redis(host: str, db_cred: DatabaseCredential,
                      existing: DiscoveredDatabase | None = None) -> DiscoveredDatabase:
    """Connect directly to Redis and discover basic stats."""
    port = db_cred.port or 6379
    db = existing or DiscoveredDatabase(engine=DatabaseEngine.REDIS, port=port, host=host)
    db.host = host
    db.discovery_method = "direct_connect"
    try:
        import redis as redis_lib  # type: ignore
    except ImportError:
        db.connection_error = "redis package not installed"
        logger.warning("redis-py not available for deep probe on %s", host)
        return db

    try:
        r = redis_lib.Redis(
            host=host, port=port,
            password=db_cred.password or None,
            socket_connect_timeout=10, decode_responses=True,
        )
        info = r.info()
        db.version = info.get("redis_version", "unknown")
        db.active_connections = info.get("connected_clients", 0)
        db.max_connections = int(info.get("maxclients", 0))
        db.edition = info.get("redis_mode", "standalone")

        # DB sizes
        db_sizes = {k: v for k, v in info.items() if k.startswith("db")}
        db.databases = list(db_sizes.keys()) if db_sizes else ["db0"]
        db.table_count = sum(v.get("keys", 0) if isinstance(v, dict) else 0
                             for v in db_sizes.values())

        # Memory as size
        used_mem = info.get("used_memory", 0)
        db.total_size_gb = round(used_mem / 1073741824, 3)
        db.size_mb = round(used_mem / 1048576, 2)

        db.instance_name = db.instance_name or "default"
        db.status = "running"
        db.connection_error = ""
        r.close()
        logger.info("Deep Redis probe on %s:%d — %.2f GB used memory",
                     host, port, db.total_size_gb)
    except Exception as exc:
        db.connection_error = str(exc)
        logger.warning("Redis deep probe failed on %s:%d — %s", host, port, exc)
    return db


_DEEP_PROBE_MAP = {
    "mysql": _deep_probe_mysql,
    "mariadb": _deep_probe_mysql,
    "postgresql": _deep_probe_postgresql,
    "mssql": _deep_probe_mssql,
    "mongodb": _deep_probe_mongodb,
    "redis": _deep_probe_redis,
}

_ENGINE_PORT_MAP = {
    3306: "mysql", 5432: "postgresql", 1433: "mssql",
    1521: "oracle", 27017: "mongodb", 6379: "redis",
}


def deep_probe_databases(
    host: str,
    db_creds: list[DatabaseCredential],
    existing_dbs: list[DiscoveredDatabase] | None = None,
) -> list[DiscoveredDatabase]:
    """Enrich or create DiscoveredDatabase entries using direct DB credentials.

    1. For each existing discovered DB, try matching DB credentials and run deep probe.
    2. For DB credentials with engine != 'auto' that didn't match any existing DB,
       probe as new databases on the host.
    3. For 'auto' credentials, try common ports to auto-detect engines.
    """
    existing = list(existing_dbs or [])
    results: list[DiscoveredDatabase] = []
    used_creds: set[int] = set()      # indices of creds already consumed

    # Pass 1: enrich existing databases
    for db in existing:
        eng_key = db.engine.value.lower()
        for ci, cred in enumerate(db_creds):
            if cred.engine in (eng_key, "auto") or (cred.port and cred.port == db.port):
                probe_fn = _DEEP_PROBE_MAP.get(eng_key)
                if probe_fn:
                    probe_fn(host, cred, existing=db)
                    used_creds.add(ci)
                    break
        results.append(db)

    # Pass 2: discover new engines from unused credentials
    existing_engines = {(db.engine.value.lower(), db.port) for db in existing}
    for ci, cred in enumerate(db_creds):
        if ci in used_creds:
            continue
        if cred.engine == "auto":
            # Try all common ports
            for port, eng_name in _ENGINE_PORT_MAP.items():
                if (eng_name, port) in existing_engines:
                    continue
                probe_fn = _DEEP_PROBE_MAP.get(eng_name)
                if probe_fn:
                    auto_cred = DatabaseCredential(
                        engine=eng_name, username=cred.username,
                        password=cred.password, port=port, host=cred.host,
                    )
                    new_db = probe_fn(host, auto_cred)
                    if not new_db.connection_error:
                        results.append(new_db)
                        existing_engines.add((eng_name, port))
        else:
            eng_key = cred.engine
            port = cred.port or DatabaseCredential(engine=eng_key, username="", password="")._default_port()
            if (eng_key, port) in existing_engines:
                continue
            probe_fn = _DEEP_PROBE_MAP.get(eng_key)
            if probe_fn:
                new_db = probe_fn(host, cred)
                if not new_db.connection_error:
                    results.append(new_db)

    return results


# ===================================================================
#  MAIN DISCOVERY ORCHESTRATOR
# ===================================================================

class GuestDiscoverer:
    """Orchestrates guest-level workload discovery across multiple VMs."""

    def __init__(self) -> None:
        self.progress: dict[str, Any] = {
            "status": "idle",
            "message": "",
            "progress": 0,
            "current_vm": "",
            "scanned": 0,
            "total": 0,
            "errors": 0,
        }
        self._lock = threading.Lock()

    def _update(self, **kwargs: Any) -> None:
        with self._lock:
            self.progress.update(kwargs)

    # ------------------------------------------------------------------

    def _try_linux_cred(self, ip: str, cred: Credential) -> tuple[list, list, list, list, list, list]:
        """Attempt all Linux probes with a single credential. Raises on auth failure."""
        ports, conns = _probe_linux_ports(ip, cred)
        databases = _probe_linux_databases(ip, cred, ports)
        web_apps = _probe_linux_webapps(ip, cred, ports)
        containers = _probe_linux_containers(ip, cred)
        orchestrators = _probe_linux_orchestrators(ip, cred)
        return ports, conns, databases, web_apps, containers, orchestrators

    def _try_windows_cred(self, ip: str, cred: Credential) -> tuple[list, list, list, list, list, list]:
        """Attempt all Windows probes with a single credential. Raises on auth failure."""
        ports, conns = _probe_win_ports(ip, cred)
        databases = _probe_win_databases(ip, cred, ports)
        web_apps = _probe_win_webapps(ip, cred, ports)
        containers = _probe_win_containers(ip, cred)
        orchestrators = _probe_win_orchestrators(ip, cred)
        return ports, conns, databases, web_apps, containers, orchestrators

    def discover_vm(self, vm_name: str, ip: str, os_family: str,
                    linux_creds: list[Credential] | Credential | None = None,
                    windows_creds: list[Credential] | Credential | None = None,
                    db_creds: list[DatabaseCredential] | None = None) -> VMWorkloads:
        """Run all probes against a single VM, trying multiple credentials.

        Accepts either a single Credential or a list of Credentials.
        Each credential is attempted in order until one succeeds.
        Database credentials are used for deep probing after OS-level discovery.
        """
        wl = VMWorkloads(vm_name=vm_name, ip_addresses=[ip], os_family=os_family)

        # Normalise to lists for uniform handling
        if isinstance(linux_creds, Credential):
            linux_creds = [linux_creds]
        if isinstance(windows_creds, Credential):
            windows_creds = [windows_creds]
        linux_creds = linux_creds or []
        windows_creds = windows_creds or []

        try:
            if os_family == "linux":
                if not linux_creds:
                    wl.scan_status = "skipped"
                    wl.scan_error = "No Linux credentials provided"
                    return wl
                wl.scan_status = "scanning"
                last_err = None
                for idx, cred in enumerate(linux_creds):
                    try:
                        logger.debug("Trying Linux cred %d/%d (%s) on %s",
                                     idx + 1, len(linux_creds), cred.username, vm_name)
                        ports, conns, dbs, webapps, containers, orchestrators = \
                            self._try_linux_cred(ip, cred)
                        wl.listening_ports = ports
                        wl.established_connections = conns
                        wl.databases = dbs
                        wl.web_apps = webapps
                        wl.container_runtimes = containers
                        wl.orchestrators = orchestrators
                        last_err = None
                        break  # success — stop trying more creds
                    except Exception as cred_exc:
                        last_err = cred_exc
                        logger.debug("Linux cred %d failed for %s: %s",
                                     idx + 1, vm_name, cred_exc)
                        continue
                if last_err:
                    raise last_err  # all creds failed

            elif os_family == "windows":
                if not windows_creds:
                    wl.scan_status = "skipped"
                    wl.scan_error = "No Windows credentials provided"
                    return wl
                wl.scan_status = "scanning"
                last_err = None
                for idx, cred in enumerate(windows_creds):
                    try:
                        logger.debug("Trying Windows cred %d/%d (%s) on %s",
                                     idx + 1, len(windows_creds), cred.username, vm_name)
                        ports, conns, dbs, webapps, containers, orchestrators = \
                            self._try_windows_cred(ip, cred)
                        wl.listening_ports = ports
                        wl.established_connections = conns
                        wl.databases = dbs
                        wl.web_apps = webapps
                        wl.container_runtimes = containers
                        wl.orchestrators = orchestrators
                        last_err = None
                        break  # success — stop trying more creds
                    except Exception as cred_exc:
                        last_err = cred_exc
                        logger.debug("Windows cred %d failed for %s: %s",
                                     idx + 1, vm_name, cred_exc)
                        continue
                if last_err:
                    raise last_err  # all creds failed

            else:
                wl.scan_status = "skipped"
                wl.scan_error = f"Unsupported OS family: {os_family}"
                return wl

            # Set vm_name on child objects
            for db in wl.databases:
                db.vm_name = vm_name
            for wa in wl.web_apps:
                wa.vm_name = vm_name
            for cr in wl.container_runtimes:
                cr.vm_name = vm_name
            for orch in wl.orchestrators:
                orch.vm_name = vm_name

            # Deep database probing with DB credentials
            if db_creds:
                logger.debug("Running deep DB probes on %s with %d DB credentials",
                             vm_name, len(db_creds))
                wl.databases = deep_probe_databases(ip, db_creds, wl.databases)
                # Re-set vm_name on any new DB entries
                for db in wl.databases:
                    db.vm_name = vm_name

            wl.scan_status = "complete"

        except Exception as exc:
            wl.scan_status = "error"
            wl.scan_error = str(exc)
            logger.warning("Guest discovery failed for %s (%s): %s", vm_name, ip, exc)

        return wl

    # ------------------------------------------------------------------

    def discover_all(
        self,
        vm_targets: list[dict],
        linux_creds: list[Credential] | Credential | None = None,
        windows_creds: list[Credential] | Credential | None = None,
        db_creds: list[DatabaseCredential] | None = None,
        max_workers: int = 5,
    ) -> WorkloadDiscoveryResult:
        """
        Discover workloads across many VMs.

        Parameters
        ----------
        vm_targets : list[dict]
            Each dict must have keys: name, ip, os_family
        linux_creds / windows_creds : list[Credential] | Credential | None
            One or more credentials for the respective OS families.
            Each credential is tried in order until one succeeds.
        db_creds : list[DatabaseCredential] | None
            Database credentials for deep probing (direct DB connections).
        max_workers : int
            Parallelism for SSH/WinRM connections.

        Returns
        -------
        WorkloadDiscoveryResult
        """
        # Normalise to lists
        if isinstance(linux_creds, Credential):
            linux_creds = [linux_creds]
        if isinstance(windows_creds, Credential):
            windows_creds = [windows_creds]
        linux_creds = linux_creds or []
        windows_creds = windows_creds or []

        result = WorkloadDiscoveryResult()
        total = len(vm_targets)
        self._update(status="scanning", message="Starting workload discovery…",
                     progress=0, scanned=0, total=total, errors=0)

        done = 0
        errors = 0

        def _scan(target: dict) -> VMWorkloads:
            nonlocal done, errors
            name = target["name"]
            ip = target["ip"]
            os = target["os_family"]
            self._update(current_vm=name, message=f"Scanning {name} ({ip})…")
            wl = self.discover_vm(name, ip, os, linux_creds, windows_creds, db_creds=db_creds)
            done += 1
            if wl.scan_status == "error":
                errors += 1
            pct = int(90 * done / max(total, 1))
            self._update(progress=pct, scanned=done, errors=errors,
                         message=f"Scanned {done}/{total} VMs…")
            return wl

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_scan, t): t for t in vm_targets}
            for future in as_completed(futures):
                try:
                    wl = future.result()
                    result.vm_workloads.append(wl)
                except Exception as exc:
                    logger.error("Unexpected error: %s", exc)
                    errors += 1

        # Build dependency graph
        self._update(status="analyzing", message="Building dependency topology…", progress=92)
        result.dependencies = _build_dependencies(result.vm_workloads)

        # Compute totals
        for vmw in result.vm_workloads:
            result.total_databases += len(vmw.databases)
            result.total_webapps += len(vmw.web_apps)
            result.total_containers += len(vmw.container_runtimes)
            result.total_orchestrators += len(vmw.orchestrators)
            if vmw.scan_status == "complete":
                result.scanned_count += 1
            elif vmw.scan_status == "error":
                result.error_count += 1
            elif vmw.scan_status == "skipped":
                result.skipped_count += 1

        self._update(status="complete", progress=100,
                     message=(f"Workload discovery complete! "
                              f"{result.total_databases} databases, "
                              f"{result.total_webapps} web apps, "
                              f"{result.total_containers} containers found."))

        return result


# ===================================================================
#  DEPENDENCY TOPOLOGY BUILDER
# ===================================================================

def _build_dependencies(vm_workloads: list[VMWorkloads]) -> list[WorkloadDependency]:
    """Cross-reference established connections against listening ports
    to build a workload dependency graph."""

    # Build a map: ip → vm_name
    ip_to_vm: dict[str, str] = {}
    for vmw in vm_workloads:
        for ip in vmw.ip_addresses:
            ip_to_vm[ip] = vmw.vm_name

    # Build a map: (vm_name, port) → workload description
    port_to_workload: dict[tuple[str, int], str] = {}
    for vmw in vm_workloads:
        for db in vmw.databases:
            port_to_workload[(vmw.vm_name, db.port)] = f"{db.engine.value}:{db.instance_name}"
        for wa in vmw.web_apps:
            if wa.port:
                port_to_workload[(vmw.vm_name, wa.port)] = f"{wa.runtime.value}:{wa.framework}"
        for lp in vmw.listening_ports:
            key = (vmw.vm_name, lp.port)
            if key not in port_to_workload:
                port_to_workload[key] = lp.process or f"port-{lp.port}"

    # Match established connections to targets
    deps: list[WorkloadDependency] = []
    seen: set[tuple[str, str, int]] = set()
    for vmw in vm_workloads:
        for conn in vmw.established_connections:
            target_vm = ip_to_vm.get(conn.remote_ip)
            if not target_vm or target_vm == vmw.vm_name:
                continue  # external or self-connection
            dedup_key = (vmw.vm_name, target_vm, conn.remote_port)
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            source_wl = conn.process or f"pid-{conn.pid}"
            target_wl = port_to_workload.get((target_vm, conn.remote_port), f"port-{conn.remote_port}")

            deps.append(WorkloadDependency(
                source_vm=vmw.vm_name,
                source_workload=source_wl,
                target_vm=target_vm,
                target_workload=target_wl,
                target_port=conn.remote_port,
            ))

    logger.info("Built %d workload dependencies", len(deps))
    return deps
