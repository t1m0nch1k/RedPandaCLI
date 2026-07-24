from unittest.mock import MagicMock
import pytest
from aios.desktop.server import DesktopIPCServer


@pytest.mark.asyncio
async def test_vision_rpc_handlers():
    """Verify vision.analyze_image and vision.capture RPC handlers in DesktopIPCServer."""
    mock_runtime = MagicMock()
    server = DesktopIPCServer(runtime=mock_runtime, host="127.0.0.1", port=8765)
    
    # Test vision.analyze_image
    res_analyze = await server._dispatch(None, "vision.analyze_image", {"image_base64": "dummy_b64"})
    assert res_analyze["status"] == "success"
    assert "summary" in res_analyze

    # Test vision.capture
    res_capture = await server._dispatch(None, "vision.capture", {})
    assert res_capture["status"] in ("success", "error")
