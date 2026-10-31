"""Pytest fixtures for WayFire test suite."""

import pytest
from wayfire.core.touch_injector import MockUInputSink


@pytest.fixture
def mock_sink() -> MockUInputSink:
    """Fixture providing a mock UInput device sink."""
    return MockUInputSink()
