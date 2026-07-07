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
# STATUS
# =====================================================

def status_line(
    label,
    value
):

    return (
        f"{label:.<30} {value}"
    )

# =====================================================
# SAFE TASKKILL
# =====================================================

def safe_taskkill(
    target: str
):

    try:

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

    except Exception:

        pass

# =====================================================
# CLEANUP
# =====================================================

def cleanup_old_processes():

    try:

        # =================================================
        # WINDOWS
        # =================================================

        if os.name == "nt":

            targets = [

                # =========================================
                # FRONTEND
                # =========================================

                "node.exe"

                # =========================================
                # Add more controlled targets if needed
                # =========================================
            ]

            for target in targets:

                safe_taskkill(
                    target
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

    creation_flags = 0

    if os.name == "nt":

        creation_flags = (
            subprocess.CREATE_NEW_PROCESS_GROUP
        )

    process = subprocess.Popen(
        command,
        cwd=cwd,
        creationflags=creation_flags
    )

    PROCESSES.append(

        {
            "name": name,
            "process": process
        }
    )

    return process

# =====================================================
# TERMINATE PROCESS
# =====================================================

def terminate_process(
    process
):

    if not process:

        return

    try:

        # =================================================
        # WINDOWS
        # =================================================

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

        # =================================================
        # UNIX
        # =================================================

        else:

            os.killpg(
                os.getpgid(process.pid),
                signal.SIGTERM
            )

    except Exception:

        pass

# =====================================================
# STOP ALL
# =====================================================

def stop_all_processes():

    for item in PROCESSES:

        terminate_process(
            item["process"]
        )

# =====================================================
# WAIT LOOP
# =====================================================

def wait_forever():

    try:

        while True:

            time.sleep(1)

    except KeyboardInterrupt:

        stop_all_processes()

        print()

        log(
            "SYSTEM",
            status_line(
                "Shutdown",
                "OK"
            ),
            "SUCCESS"
        )

        sys.exit(0)
