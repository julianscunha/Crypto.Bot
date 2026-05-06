# -*- coding: utf-8 -*-

import os

from alembic import command
from alembic.config import Config


def run():

    alembic_cfg = Config("alembic.ini")

    command.upgrade(
        alembic_cfg,
        "head"
    )

    print("[OK] Database migrated")


if __name__ == "__main__":
    run()