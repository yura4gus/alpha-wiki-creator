from pathlib import Path
from tools.classify import classify_llm_fallback


def test_llm_fallback_returns_none_without_api_key(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    p = tmp_path / "weird.txt"
    p.write_text("ambiguous content")
    result = classify_llm_fallback(p)
    assert result is None
