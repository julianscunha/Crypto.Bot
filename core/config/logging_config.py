# -*- coding: utf-8 -*-

from core.config.settings import (
    settings
)

from core.config.signal_quality_config import (
    positive_int
)

LOGGING_CONFIG = {

    # =================================================
    # PATHS
    # =================================================

    "root_directory_depth": 2,

    "logs_directory": "logs",

    "runtime_log_filename": "runtime.log",

    "error_log_filename": "errors.log",

    # =================================================
    # VISUAL
    # =================================================

    "category_width": 18,

    "section_width": 60,

    "timestamp_format":
        "%Y-%m-%d %H:%M:%S",

    # =================================================
    # FILE LOGGING
    # =================================================

    "max_log_file_size":

        positive_int(

            getattr(
                settings,
                "MAX_LOG_FILE_SIZE",
                1_000_000
            ),

            1_000_000
        ),

    "log_backup_count":

        positive_int(

            getattr(
                settings,
                "LOG_BACKUP_COUNT",
                3
            ),

            3
        ),

    "file_log_format":

        "%(message)s"
}
