import paramiko
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict

executor = ThreadPoolExecutor(max_workers=5)


def ssh_command(host: str, port: int, username: str, password: str, cmd: str, cmd_timeout: int = 10) -> Optional[str]:
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, port=port, username=username, password=password, timeout=10)
        _, stdout, stderr = client.exec_command(cmd, timeout=cmd_timeout)
        output = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        client.close()
        return output if output else err
    except Exception as e:
        return f"ERROR: {str(e)}"


async def async_ssh(host: str, port: int, username: str, password: str, cmd: str, cmd_timeout: int = 10) -> Optional[str]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, ssh_command, host, port, username, password, cmd, cmd_timeout)


async def get_cpu_temp(host: str, port: int, username: str, password: str) -> str:
    # Try common paths for CPU temp
    cmds = [
        "cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null",
        "cat /sys/devices/virtual/thermal/thermal_zone0/temp 2>/dev/null",
    ]
    for cmd in cmds:
        result = await async_ssh(host, port, username, password, cmd)
        if result and result != "" and not result.startswith("ERROR") and result != "cat: /sys/class/thermal/thermal_zone0/temp: No such file or directory":
            try:
                temp = float(result) / 1000
                return f"{temp:.1f}°C"
            except ValueError:
                return result
    return "N/A"


async def get_ram_usage(host: str, port: int, username: str, password: str) -> str:
    result = await async_ssh(host, port, username, password,
                             "free -m | awk 'NR==2{printf \"%.1f%% (used %dMB / total %dMB)\", $3*100/$2, $3, $2}'")
    if result and not result.startswith("ERROR"):
        return result
    return "N/A"


async def get_storage_usage(host: str, port: int, username: str, password: str) -> str:
    result = await async_ssh(host, port, username, password,
                             "df -h / | awk 'NR==2{printf \"%s (used %s / total %s)\", $5, $3, $2}'")
    if result and not result.startswith("ERROR"):
        return result
    return "N/A"


async def get_uptime(host: str, port: int, username: str, password: str) -> str:
    result = await async_ssh(host, port, username, password, "uptime -p")
    if result and not result.startswith("ERROR"):
        return result
    return "N/A"


async def get_load_average(host: str, port: int, username: str, password: str) -> str:
    result = await async_ssh(host, port, username, password,
                             "cat /proc/loadavg | awk '{printf \"1m: %s, 5m: %s, 15m: %s\", $1, $2, $3}'")
    if result and not result.startswith("ERROR"):
        return result
    return "N/A"


async def check_connection(host: str, port: int, username: str, password: str) -> str:
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, port=port, username=username, password=password, timeout=5)
        client.close()
        return "✅ Connected"
    except Exception as e:
        return f"❌ Failed: {str(e)}"


async def ping_test(host: str, port: int, username: str, password: str, target: str = "8.8.8.8", count: int = 4) -> str:
    result = await async_ssh(host, port, username, password,
                             f"ping -c {count} -W 3 {target} 2>&1")
    if result and not result.startswith("ERROR"):
        for line in result.splitlines():
            if "packet loss" in line:
                return line.strip()
        return result.splitlines()[-1] if result.splitlines() else "No output"
    return "Ping result unavailable"


async def speedtest_result(host: str, port: int, username: str, password: str) -> str:
    # Check available speedtest tools
    check_cmd = (
        'if command -v speedtest-cli >/dev/null 2>&1; then '
        'echo "speedtest-cli"; '
        'elif command -v speedtest >/dev/null 2>&1; then '
        'echo "speedtest"; '
        'else echo "not_found"; fi'
    )
    tool = await async_ssh(host, port, username, password, check_cmd)
    if not tool or tool.startswith("ERROR"):
        return "Speedtest unavailable (SSH error)"

    if tool == "not_found":
        return (
            "Speedtest tidak tersedia.\n"
            "Install dengan:\n"
            "  apt install speedtest-cli\n"
            "Atau:\n"
            "  pip install speedtest-cli"
        )

    if tool == "speedtest-cli":
        cmd = 'speedtest-cli --simple 2>&1'
    else:
        cmd = 'speedtest --progress=no --format=human 2>&1'

    result = await async_ssh(host, port, username, password, cmd, cmd_timeout=60)
    if result and not result.startswith("ERROR"):
        return result
    return "Speedtest gagal (mungkin koneksi lambat atau timeout)"


async def reboot_stb(host: str, port: int, username: str, password: str) -> str:
    result = await async_ssh(host, port, username, password, "sudo reboot")
    if result and result.startswith("ERROR"):
        return result
    return "✅ Reboot command sent"


async def get_all_status(host: str, port: int, username: str, password: str) -> Dict[str, str]:
    tasks = {
        "cpu_temp": get_cpu_temp(host, port, username, password),
        "ram": get_ram_usage(host, port, username, password),
        "storage": get_storage_usage(host, port, username, password),
        "uptime": get_uptime(host, port, username, password),
        "load": get_load_average(host, port, username, password),
        "connection": check_connection(host, port, username, password),
    }
    results = {}
    for key, coro in tasks.items():
        results[key] = await coro
    return results
