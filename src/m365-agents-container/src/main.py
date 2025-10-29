# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

"""Legacy entrypoint delegating to new modular bootstrap."""
from .app.bootstrap import main as _bootstrap_main  # noqa: F401


def main():  # pragma: no cover - thin wrapper
    _bootstrap_main()


if __name__ == "__main__":
    main()
