# -*- coding: utf-8 -*-

import json

from pathlib import Path


class ReportEngine:

    def generate(
        self,
        metrics: dict,
        output_path: str
    ):

        Path(
            output_path
        ).parent.mkdir(
            parents=True,
            exist_ok=True
        )

        with open(
            output_path,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                metrics,
                f,
                indent=4
            )