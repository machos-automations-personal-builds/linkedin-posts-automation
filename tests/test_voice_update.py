"""Tests for generator/voice_update.py"""

from unittest.mock import patch

import pytest

import generator.draft as draft_module
import generator.voice_update as voice_update


def _patch_paths(monkeypatch, tmp_path):
    guide_path = tmp_path / "voice_guide.txt"
    guide_path.write_text("Original guide content.", encoding="utf-8")
    history_dir = tmp_path / "voice_guide_history"

    monkeypatch.setattr(draft_module, "VOICE_GUIDE_PATH", guide_path)
    monkeypatch.setattr(voice_update, "VOICE_GUIDE_PATH", guide_path)
    monkeypatch.setattr(voice_update, "VOICE_GUIDE_HISTORY_DIR", history_dir)
    return guide_path, history_dir


def test_update_voice_guide_backs_up_and_writes(tmp_path, monkeypatch):
    guide_path, history_dir = _patch_paths(monkeypatch, tmp_path)

    with patch("generator.voice_update.generate_text", return_value="Updated guide content.") as mock_gen:
        result = voice_update.update_voice_guide({"title": "My Post", "content": "Post body."})

    assert result == "Updated guide content."
    assert guide_path.read_text(encoding="utf-8") == "Updated guide content."

    backups = list(history_dir.glob("voice_guide_*.txt"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "Original guide content."

    mock_gen.assert_called_once()
    assert mock_gen.call_args.kwargs.get("temperature") == voice_update.VOICE_UPDATE_TEMPERATURE


def test_update_voice_guide_raises_and_preserves_guide_on_failure(tmp_path, monkeypatch):
    guide_path, _ = _patch_paths(monkeypatch, tmp_path)

    with patch("generator.voice_update.generate_text", side_effect=Exception("boom")):
        with pytest.raises(Exception, match="boom"):
            voice_update.update_voice_guide({"title": "My Post", "content": "Post body."})

    assert guide_path.read_text(encoding="utf-8") == "Original guide content."
