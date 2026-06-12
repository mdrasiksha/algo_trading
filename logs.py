"""Logging helpers for scripts that need consistent console output."""

import logging
import os
import sys


def setup_logging(name: str = "algo_trading") -> logging.Logger:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger(name)
