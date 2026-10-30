"""Backwards-compatibility shim for the old `mangroveai` import path.

The Mangrove Python SDK kept its PyPI distribution name as `mangroveai`
but renamed the import path to `mangrove_ai` starting in v1.0.2 so
the import is unambiguous next to the MangroveAI backend repo.

This shim aliases the old name to the new one at module-import time,
so `from mangroveai import MangroveAI` and `from mangroveai.models
import Whatever` both continue to work — they're forwarded to the
`mangrove_ai` package and emit a DeprecationWarning on first import.

Retained in v2.x. Removal requires an announced future major release.
"""
from __future__ import annotations

import sys
import warnings

import mangrove_ai as _mangrove_ai
import mangrove_ai.models  # Load the public model modules before aliasing them.

warnings.warn(
    "`mangroveai` is the deprecated import path. Use `from mangrove_ai import ...` "
    "instead. The PyPI distribution name `mangroveai` is unchanged — only the "
    "import path was renamed. Removal requires an announced future major release.",
    DeprecationWarning,
    stacklevel=2,
)

# Alias the public models and already loaded modules too. Aliasing only the
# package makes Python reload models under the old name, creating incompatible
# class identities for isinstance checks and exception handling.
for _name, _module in list(sys.modules.items()):
    if _name.startswith("mangrove_ai."):
        sys.modules["mangroveai." + _name.removeprefix("mangrove_ai.")] = _module
sys.modules[__name__] = _mangrove_ai
