"""Stage 2 environment and editable-package checks only."""

from importlib.metadata import metadata, version
from pathlib import Path
import sys

import duetshift


def test_python_version():
    assert sys.version_info[:2] == (3, 12), "Activate duetshift-dev (Python 3.12)."


def test_package_imports_from_this_repository():
    expected = Path(__file__).resolve().parents[1] / "src" / "duetshift" / "__init__.py"
    assert Path(duetshift.__file__).resolve() == expected


def test_package_basics():
    assert duetshift.__name__ == "duetshift"
    assert version("duetshift") == "0.1.0"
    assert set(metadata("duetshift")["Requires-Python"].split(",")) == {">=3.12", "<3.13"}
