import os
import pytest

os.environ["LIVEO_TEST_MODE"] = "1"

import backend.server as srv
from backend.debug import clear_debug_logs


@pytest.fixture(autouse=True)
def _reset_server_state():
    """매 테스트 전에 서버 전역 상태를 초기화한다."""
    srv._candidates.clear()
    srv._generated.clear()
    srv._settings = srv.Settings()
    srv._reset_runtime_state()
    clear_debug_logs()
    yield
