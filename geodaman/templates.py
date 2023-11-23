# -*- coding: utf-8 -*-
"""Module Name.

Author: travis
Date: Wed Nov 22 07:31:27 PM MST 2023
"""
from pathlib import Path


HOME = Path("/home/travis/github/geodaman")


class ATemplate:
    """A docstring."""

    def __init__(self):
        """Initialize an ATemplate object."""

    def __repr__(self):
        """Return an ATemplate object representation string."""
        address = hex(id(self))
        msgs = [f"\n   {k}={v}" for k, v in self.__dict__.items()]
        msg = ", ".join(msgs)
        return f"<ATemplate object at {address}>: {msg}"


def main():
    """A docstring."""


if __name__ == "__main__":
    pass
