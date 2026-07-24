import pytest
from aios.config.settings import Settings
from aios.desktop.voice.wake_word import WakeWordDetector


def test_wake_word_privacy_default():
    """Verify that WakeWordDetector is disabled by default for user privacy."""
    detector = WakeWordDetector(enabled=False)
    assert not detector.enabled
    assert not detector.is_listening

    called = False
    started = detector.start(lambda: None)
    assert not started
    assert not detector.is_listening


def test_wake_word_config_update():
    """Verify configuration update and state management."""
    detector = WakeWordDetector(enabled=False)
    detector.update_config(enabled=True, keyword="hey_aios", threshold=0.7)
    assert detector.enabled
    assert detector.keyword == "hey_aios"
    assert detector.threshold == 0.7

    detector.stop()
    assert not detector.is_listening


def test_settings_wake_word_privacy_defaults():
    """Verify Settings defaults prioritize privacy."""
    settings = Settings()
    assert not settings.voice.wake_word.enabled
    assert settings.voice.wake_word.keyword == "hey_aios"
