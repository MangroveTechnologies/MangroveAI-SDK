"""Backwards-compatibility shim for the old `mangroveai` import path.

The Mangrove Python SDK kept its PyPI distribution name as `mangroveai`
but renamed the import path to `mangrove_ai` starting in v1.0.2 so
the import is unambiguous next to the MangroveAI backend repo.

This shim aliases the old name to the new one at module-import time,
so `from mangroveai import MangroveAI` and `from mangroveai.models
import Whatever` both continue to work — they're forwarded to the
`mangrove_ai` package and emit a DeprecationWarning on first import.

Will be removed in v2.0.0.
"""
from __future__ import annotations

import sys
import warnings

import mangrove_ai as _mangrove_ai

warnings.warn(
    "`mangroveai` is the deprecated import path. Use `from mangrove_ai import ...` "
    "instead. The PyPI distribution name `mangroveai` is unchanged — only the "
    "import path was renamed. This shim will be removed in v2.0.0.",
    DeprecationWarning,
    stacklevel=2,
)

# Alias at the module level so submodule access (mangroveai.models,
# mangroveai._services, etc.) resolves to the mangrove_ai equivalents.
sys.modules[__name__] = _mangrove_ai
