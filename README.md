# Katsudon 🍚🐖

*A Sysmon-based helper script for **dynamic malware analysis**, inspired by [Noriben](https://github.com/Rurik/Noriben).*  

Katsudon installs a dedicated Sysmon profile, collects **detailed Sysmon telemetry** while your sample runs, and, on `Ctrl+C` exports the log to a TSV before restoring (or uninstalling) Sysmon.
Its key advantage is that it surfaces **Process Access events (Event ID 10)**—calls such as `WriteProcessMemory`, `VirtualAllocEx`, and others that can be overlooked in typical Procmon-based workflows.

That said, the resulting TSV is noticeably busier than Noriben’s streamlined Procmon output and can be a bit harder to scan at a glance.

## How It Works
1. **Run `katsudon.py`.**
   * The script relaunches itself with administrative rights if necessary.

2. **Sysmon handling**
   * If **Sysmon is already running**: backs up the current configuration **and** log-size limit, then **updates** the configuration with `sysmon_config.xml`.  
   * If **Sysmon is not running**: installs Sysmon with `sysmon_config.xml`.

3. **Preparation**
   * Clears the *Microsoft-Windows-Sysmon/Operational* channel.
   * Sets the log-size limit (default = 1 GiB).

4. **Analysis window**
   * Execute your malware however you like.  
   * Press **`Ctrl+C`** when finished.

5. **Shutdown**
   * Exports all events to `Katsudon_<date>__<time>.tsv`.
   * Restores the original Sysmon state or uninstalls it—no artefacts left behind.

## Requirements
* **Python 3.12** (older 3.x should also work)
* **Sysinternals Sysmon v15+** in your `%PATH%` (tested with Sysmon64 v15.15)

## How to Use
1. Place `katsudon.py` and `sysmon_config.xml` in the same folder.  
2. Double-click `katsudon.py` **or** launch it from *Command Prompt* / *Windows Terminal*.

## Optional Third-Party Software
* **[FLARE-FakeNet-NG](https://github.com/mandiant/flare-fakenet-ng)** – a user-mode network simulator that simplifies traffic capture and redirection during dynamic analysis.
