import shutil
import socket
import subprocess
from datetime import timedelta

import psutil


def _safe_run(command: list[str]) -> str | None:
    if not shutil.which(command[0]):
        return None
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=5, check=False)
        output = result.stdout.strip() or result.stderr.strip()
        return output or None
    except Exception:
        return None



def _get_local_ips() -> list[str]:
    addresses = []
    for _, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                addresses.append(addr.address)
    return sorted(set(addresses))



def _get_tailscale_ip() -> str | None:
    output = _safe_run(["tailscale", "ip", "-4"])
    if output:
        return output.splitlines()[0].strip()
    return None



def _get_service_status(service_name: str = "discord-bot") -> str | None:
    output = _safe_run(["systemctl", "is-active", service_name])
    return output



def get_system_status() -> dict:
    vm = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    boot_time = timedelta(seconds=int(psutil.boot_time()))
    uptime_seconds = int(psutil.time.time() - psutil.boot_time())
    uptime = str(timedelta(seconds=uptime_seconds))

    return {
        "hostname": socket.gethostname(),
        "uptime": uptime,
        "cpu_percent": psutil.cpu_percent(interval=0.5),
        "memory_percent": vm.percent,
        "memory_used_gb": round(vm.used / (1024 ** 3), 2),
        "memory_total_gb": round(vm.total / (1024 ** 3), 2),
        "disk_percent": disk.percent,
        "disk_used_gb": round(disk.used / (1024 ** 3), 2),
        "disk_total_gb": round(disk.total / (1024 ** 3), 2),
        "local_ips": _get_local_ips(),
        "tailscale_ip": _get_tailscale_ip(),
        "service_status": _get_service_status(),
    }
