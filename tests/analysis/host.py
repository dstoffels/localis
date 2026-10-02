import os
import platform
from importlib import metadata


def _proc_field(path: str, key: str) -> str | None:
    try:
        with open(path) as f:
            for line in f:
                if line.startswith(key):
                    return line.split(":", 1)[1].strip()
    except OSError:
        return None
    return None


def host_fingerprint() -> dict[str, object]:
    """Describes the machine and interpreter a timing or memory measurement ran on."""
    mem_total = _proc_field("/proc/meminfo", "MemTotal")
    try:
        version = metadata.version("localis")
    except metadata.PackageNotFoundError:
        version = None
    return {
        "os": f"{platform.system()} {platform.release()}",
        "machine": platform.machine(),
        "cpu": _proc_field("/proc/cpuinfo", "model name") or platform.processor() or None,
        "cpu_count": os.cpu_count(),
        "memory_total_bytes": int(mem_total.split()[0]) * 1024 if mem_total else None,
        "python": platform.python_version(),
        "localis": version,
    }
