#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import ctypes
import platform
import re
import time
import subprocess
import sys
from datetime import datetime
from shutil import which

SYSMON_CFG = "sysmon_config.xml"
OUTPUT_PREFIX = "Katsudon"
EVENTLOG_NAME = "Microsoft-Windows-Sysmon/Operational"
MAX_LOG_SIZE_BYTES  = 1 * 1024 * 1024 * 1024 # 1 GiB

def ensure_admin():
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    except AttributeError:
        is_admin = True
    if not is_admin:
        params = " ".join(map(lambda a: f'"{a}"', sys.argv))
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
        sys.exit()

def run(cmd, check=True, **kw):
    capture = 'stdout' not in kw and 'stderr' not in kw
    return subprocess.run(cmd, text=True, capture_output=capture, check=check, **kw)

def get_arch_and_binary():
    is_x64 = platform.machine().endswith("64")
    exe = "Sysmon64.exe" if is_x64 else "Sysmon.exe"
    if which(exe) is None:
        sys.exit(f"[!] {exe} not found in PATH")
    service = "Sysmon64" if is_x64 else "Sysmon"
    return exe, service

def sysmon_running(service):
    cp = run(["sc", "query", service], check=False)
    return "RUNNING" in cp.stdout

def get_current_log_size():
    cp = run(["wevtutil", "gl", EVENTLOG_NAME])
    m  = re.search(r"maxSize:\s+(\d+)", cp.stdout)
    return int(m.group(1)) if m else None

def set_log_size(size):
    run(["wevtutil", "sl", EVENTLOG_NAME, f"/ms:{size}"])

def clear_eventlog():
    run(["wevtutil", "cl", EVENTLOG_NAME])

def backup_sysmon_config(exe, dst):
    with open(dst, "w", encoding="utf-8") as fh:
        run([exe, "-c"], stdout=fh)

def restore_sysmon_config(exe, cfg_path):
    if cfg_path:
        run([exe, "-c", cfg_path])

def install_or_update_sysmon(exe, running):
    arg = "-c" if running else "-i"
    if arg == "-i":
        run([exe, arg, SYSMON_CFG], stdout=None, stderr=None)
    else:
        run([exe, arg, SYSMON_CFG])

def uninstall_sysmon(exe):
    run([exe, "-u"])
    full_path = which(exe) or exe
    run(["wevtutil", "um", full_path], check=False)

def export_eventlog_to_tsv(tsv_path):
    ps_cmd = (
        f"[System.IO.File]::WriteAllLines('{tsv_path}',"
        f"(Get-WinEvent -LogName '{EVENTLOG_NAME}' -Oldest | "
        f"%{{\"{{0}}`t{{1}}`t{{2}}\" -f $_.TimeCreated.ToString('yyyy-MM-dd HH:mm:ss'),"
        f"$_.Id, ($_.Message -replace '\\r?\\n',' ')}}),"
        f"(New-Object System.Text.UTF8Encoding $false))"
    )
    run(["powershell", "-NoLogo", "-NoProfile", "-Command", ps_cmd])

def main():
    ensure_admin()
    exe, service = get_arch_and_binary()
    was_running  = sysmon_running(service)

    orig_log_size = get_current_log_size() if was_running else None
    original_cfg_path = None
    if was_running:
        print("[*] Existing Sysmon detected – backing up configuration and log size")
        original_cfg_path = backup_sysmon_config(exe)

        print(f"    Current log size limit: {orig_log_size} bytes")
        print(f"    Current Config file: {original_cfg_path}")
    else:
        print("[*] Sysmon is not running – installing a temporary instance")

    install_or_update_sysmon(exe, was_running)

    print(f"[*] Setting {EVENTLOG_NAME} max size to {MAX_LOG_SIZE_BYTES} bytes")
    set_log_size(MAX_LOG_SIZE_BYTES)

    print("[*] Clearing event log")
    clear_eventlog()

    print("\n=== Ready – press Ctrl+C to finish capture ===\n")
    try:
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[*] Capture finished – exporting log to TSV")
        now = datetime.now()
        output_tsv = (f"{OUTPUT_PREFIX}_{now.strftime('%d_%b_%y')}"
                      f"__{now.strftime('%H_%M_%S%f')}.tsv")
        export_eventlog_to_tsv(output_tsv)
        print(f"    -> {output_tsv}")

    print("[*] Performing cleanup")
    if was_running:
        print("    Restoring original Sysmon configuration/log size")
        restore_sysmon_config(exe, original_cfg_path)
        if orig_log_size:
            set_log_size(orig_log_size)
    else:
        print("    Uninstalling Sysmon")
        uninstall_sysmon(exe)

    print("[+] Completed")

if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        sys.exit(f"[!] Command failed: {e.cmd}\n{e.stderr}")
