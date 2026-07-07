# -*- coding: utf-8 -*-

from colorama import (
    Fore,
    Style,
    init
)

init(autoreset=True)


class ReportRenderer:

    WIDTH = 60

    METRIC_WIDTH = 30

    # =====================================================
    # HEADER
    # =====================================================

    @staticmethod
    def print_header(
        title: str
    ):

        line = (
            "=" * ReportRenderer.WIDTH
        )

        print()

        print(
            Fore.LIGHTCYAN_EX
            + line
            + Style.RESET_ALL
        )

        print(
            Fore.LIGHTCYAN_EX
            + title.center(
                ReportRenderer.WIDTH
            )
            + Style.RESET_ALL
        )

        print(
            Fore.LIGHTCYAN_EX
            + line
            + Style.RESET_ALL
        )

    # =====================================================
    # SECTION
    # =====================================================

    @staticmethod
    def print_section(
        title: str
    ):

        print()

        print(
            Fore.LIGHTYELLOW_EX
            + f"[{title}]"
            + Style.RESET_ALL
        )

    # =====================================================
    # METRIC
    # =====================================================

    @staticmethod
    def print_metric(
        label: str,
        value,
        rating: str | None = None
    ):

        line = (
            f"{label} "
            .ljust(
                ReportRenderer.METRIC_WIDTH,
                "."
            )
            + f" {value}"
        )

        # =================================================
        # RATING
        # =================================================

        if rating:

            rating_upper = (
                rating.upper()
            )

            # =============================================
            # POSITIVE
            # =============================================

            if rating_upper in [
                "ROBUST",
                "STRONG",
                "GOOD",
                "EXCELLENT"
            ]:

                rating_color = (
                    Fore.GREEN
                )

            # =============================================
            # NEGATIVE
            # =============================================

            elif rating_upper in [
                "POOR",
                "WEAK",
                "LOSING",
                "CRITICAL",
                "SUSPICIOUS",
                "HIGH",
                "EXTREMELY_HIGH"
            ]:

                rating_color = (
                    Fore.RED
                )

            # =============================================
            # NEUTRAL
            # =============================================

            else:

                rating_color = (
                    Fore.LIGHTYELLOW_EX
                )

            line += (
                " ("
                + rating_color
                + rating
                + Fore.LIGHTWHITE_EX
                + ")"
            )

        print(
            Fore.LIGHTWHITE_EX
            + line
            + Style.RESET_ALL
        )

    # =====================================================
    # VERDICT
    # =====================================================

    @staticmethod
    def print_verdict(
        status: str,
        recommendation: str
    ):

        print()

        status_upper = (
            status.upper()
        )

        # =================================================
        # STATUS COLORS
        # =================================================

        if status_upper in [
            "ROBUST",
            "PROMISING"
        ]:

            status_color = (
                Fore.GREEN
            )

        elif status_upper in [
            "INSUFFICIENT_DATA",
            "SUSPICIOUS"
        ]:

            status_color = (
                Fore.LIGHTYELLOW_EX
            )

        else:

            status_color = (
                Fore.RED
            )

        print(
            Fore.LIGHTCYAN_EX
            + "[FINAL VERDICT]"
            + Style.RESET_ALL
        )

        print()

        print(
            Fore.LIGHTWHITE_EX
            + "Status "
            .ljust(
                ReportRenderer.METRIC_WIDTH,
                "."
            )
            + status_color
            + f" {status}"
            + Style.RESET_ALL
        )

        print()

        print(
            Fore.LIGHTCYAN_EX
            + "Recommendation:"
            + Style.RESET_ALL
        )

        print(
            Fore.LIGHTWHITE_EX
            + recommendation
            + Style.RESET_ALL
        )

    # =====================================================
    # FOOTER
    # =====================================================

    @staticmethod
    def print_footer():

        print()

        print(
            Fore.LIGHTCYAN_EX
            + "=" * ReportRenderer.WIDTH
            + Style.RESET_ALL
        )
