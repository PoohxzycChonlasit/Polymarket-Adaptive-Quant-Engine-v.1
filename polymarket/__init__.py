"""Polymarket package."""

import sys
import platform

# Mock platform._wmi_query to avoid Windows WMI query hangs
# in containerized/sandboxed environments.
if sys.platform == 'win32':
    def _mock_wmi_query(*args, **kwargs):
        raise OSError("WMI queries disabled to prevent import hang")
    platform._wmi_query = _mock_wmi_query
