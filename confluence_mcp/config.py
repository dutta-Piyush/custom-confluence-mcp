from __future__ import annotations

import os
import pathlib

CONFLUENCE_URL: str = os.environ.get("CONFLUENCE_URL", "")
CONFLUENCE_PAT: str = os.environ.get("CONFLUENCE_PAT", "")
VERIFY_SSL: bool = os.environ.get("CONFLUENCE_VERIFY_SSL", "false").lower() == "true"

# Absolute path to the project root (one level above this package)
PROJECT_ROOT: pathlib.Path = pathlib.Path(__file__).parent.parent
DIAGRAMS_DIR: str = str(PROJECT_ROOT / "diagrams")
