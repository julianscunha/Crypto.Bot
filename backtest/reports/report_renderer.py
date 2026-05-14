# -*- coding: utf-8 -*-

from colorama import (
    Fore,
    Style,
    init
)

init(autoreset=True)


class ReportRenderer:

    # =====================================================
    # HEADER
    # =====================================================

    @staticmethod
    def print_header(
        title: str
    ):

        print()

        print(
            Fore.LIGHTWHITE_EX
            + "=" * 60
        )

        print(
            Fore.CYAN
            + title.center(60)
        )

        print(
            Fore.LIGHTWHITE_EX
            + "=" * 60
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
            Fore.YELLOW
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
            .ljust(30, ".")
            + f" {value}"
        )

        if rating:

            # =============================================
            # RATING COLOR
            # =============================================

            rating_upper = rating.upper()

            if rating_upper in [
                "ROBUST",
                "STRONG",
                "GOOD",
                "EXCELLENT"
            ]:

                rating_color = (
                    Fore.GREEN
                )

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

            else:

                rating_color = (
                    Fore.YELLOW
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

        # =============================================
        # STATUS COLOR
        # =============================================

        status_upper = (
            status.upper()
        )

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
                Fore.YELLOW
            )

        else:

            status_color = (
                Fore.RED
            )

        print(
            Fore.CYAN
            + "[FINAL VERDICT]"
            + Style.RESET_ALL
        )

        print()

        print(
            Fore.LIGHTWHITE_EX
            + "Status "
            .ljust(30, ".")
            + status_color
            + f" {status}"
            + Style.RESET_ALL
        )

        print()

        print(
            Fore.CYAN
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
            Fore.LIGHTWHITE_EX
            + "=" * 60
            + Style.RESET_ALL
        )