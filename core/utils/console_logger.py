# -*- coding: utf-8 -*-

from colorama import (
    Fore,
    Style
)


def log(
    tag: str,
    message: str,
    color=Fore.WHITE
):

    formatted_tag = (
        f"[{tag}]"
        .ljust(24)
    )

    print(
        color +
        formatted_tag +
        Style.RESET_ALL +
        message
    )