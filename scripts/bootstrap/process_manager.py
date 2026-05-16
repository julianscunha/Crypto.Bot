# -*- coding: utf-8 -*-

import os
import signal
import subprocess
import sys
import time

from core.utils.console_logger import (
    log
)

# =====================================================
# PROCESS REGISTRY
# =====================================================

PROCESSES = []

# =====================================================
# STATUS LINE
# =====================================================

def status_line(label, value):

    return f"{label:.<30} {value}"

# =====================================================
# CLEAN OLD PROCESSES
# =====================================================

def cleanup_old_processes():

    try:

        if os.name == "nt":

            targets = [
                "node.exe"
            ]

            for target in targets:

                subprocess.run(
                    [
                        "taskkill",
                        "/F",
                        "/IM",
                        target
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

        log(
            "SYSTEM",
            status_line(
                "Processes",
                "OK"
            ),
            "SUCCESS"
        )

    except Exception:

        log(
            "SYSTEM",
            status_line(
                "Processes",
                "WARNING"
            ),
            "WARNING"
        )

# =====================================================
# START PROCESS
# =====================================================

def start_process(
    name: str,
    command: list,
    cwd=None
):

    process = subprocess.Popen(
        command,
        cwd=cwd,
        creationflags=(
            subprocess.CREATE_NEW_PROCESS_GROUP
            if os.name == "nt"
            else 0
        )
    )

    PROCESSES.append(
        {
            "name": name,
            "process": process
        }
    )

    return process

# =====================================================
# STOP ALL
# =====================================================

def stop_all_processes():

    for item in PROCESSES:

        process = item["process"]

        try:

            if os.name == "nt":

                subprocess.run(
                    [
                        "taskkill",
                        "/F",
                        "/T",
                        "/PID",
                        str(process.pid)
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

            else:

                os.killpg(
                    os.getpgid(process.pid),
                    signal.SIGTERM
                )

        except Exception:

            pass

# =====================================================
# WAIT
# =====================================================

def wait_forever():

    try:

        while True:

            time.sleep(1)

    except KeyboardInterrupt:

        stop_all_processes()

        sys.exit(0)