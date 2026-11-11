"""Legacy imports must preserve identity without owning the engine directory."""
import subprocess
import sys
import textwrap

import pytest


@pytest.mark.parametrize("first", ["mangroveai", "mangrove_ai"])
def test_flat_legacy_shim_preserves_public_module_and_class_identity(first):
    # Separate processes exercise both first-import orders without sys.modules
    # from another test hiding duplicate models or a missing compatibility shim.
    program = textwrap.dedent(f"""
        import importlib
        import importlib.util
        from pathlib import Path
        import warnings

        spec = importlib.util.find_spec("mangroveai")
        assert Path(spec.origin).name == "mangroveai.py"
        assert spec.submodule_search_locations is None
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", DeprecationWarning)
            importlib.import_module({first!r})
            import mangrove_ai
            import mangroveai
            from mangroveai.models import UserMetrics as LegacyMetrics
            from mangroveai.models.strategies import StrategyDetail as LegacyDetail
            from mangroveai.exceptions import APIError as LegacyError
        from mangrove_ai.models import UserMetrics
        from mangrove_ai.models.strategies import StrategyDetail
        assert mangroveai is mangrove_ai
        assert LegacyMetrics is UserMetrics
        assert LegacyDetail is StrategyDetail
        assert LegacyError is mangrove_ai.APIError
        assert any("deprecated import path" in str(warning.message) for warning in caught)
    """)
    result = subprocess.run([sys.executable, "-c", program], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
