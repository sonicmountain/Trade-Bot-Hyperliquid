"""Command-line entry point for the Hyperliquid Copy-Trade Verifier.

Parses arguments, loads configuration and launches the Textual TUI.

This module is intentionally thin: all verification logic lives in
:mod:`hl_copytrade_verifier.core`, all rendering in :mod:`hl_copytrade_verifier.tui`.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from hl_copytrade_verifier import __version__
from hl_copytrade_verifier.config import Config, default_config_path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hl-verify",
        description=(
            "Hyperliquid Copy-Trade Verifier — a read-only terminal tool that "
            "independently re-derives trader ROI/PnL/drawdown from public fills "
            "before you copy-trade."
        ),
    )
    parser.add_argument(
        "--version", "-V", action="version", version=f"hl-copytrade-verifier {__version__}"
    )
    parser.add_argument(
        "--config", type=Path, default=None, help="Path to config.toml (default: ~/.hl-verify/config.toml)."
    )
    parser.add_argument(
        "--trader", type=str, default=None, help="Open directly on a public trader address."
    )
    parser.add_argument(
        "--theme",
        choices=["dark", "light", "hyperliquid"],
        default=None,
        help="Override the UI theme.",
    )
    parser.add_argument(
        "--demo", action="store_true", help="Run fully offline with the bundled demo dataset."
    )
    parser.add_argument("--no-color", action="store_true", help="Force-disable color output.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    # Environment overrides (lower precedence than explicit flags).
    demo = args.demo or os.environ.get("HL_VERIFY_DEMO", "") == "1"
    no_color = args.no_color or os.environ.get("HL_VERIFY_NO_COLOR", "") == "1"

    config_path = args.config or Path(
        os.environ.get("HL_VERIFY_CONFIG", str(default_config_path()))
    )
    config = Config.load(config_path, demo=demo, no_color=no_color, theme_override=args.theme)

    # Lazy import: Textual is only needed when we actually launch the UI.
    try:
        from hl_copytrade_verifier.tui.app import VerifierApp  # noqa: WPS433 (intentional local import)
    except ImportError as exc:  # pragma: no cover - depends on the environment
        print(
            f"error: TUI dependencies are not installed ({exc}). "
            "Run `pip install -e .` first.",
            file=sys.stderr,
        )
        return 2

    app = VerifierApp(config=config, initial_trader=args.trader)
    app.run()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
