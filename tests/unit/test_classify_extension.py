from pathlib import Path
from tools.classify import classify


def test_classify_openapi(tmp_path: Path):
    p = tmp_path / "auth.yaml"
    p.write_text("openapi: 3.0.0\ninfo:\n  title: Auth\n")
    a = classify(p)
    assert a.kind == "openapi"
    assert a.suggested_slot == "contracts/rest"


def test_classify_proto(tmp_path: Path):
    p = tmp_path / "svc.proto"
    p.write_text("syntax = \"proto3\";\nservice X {}")
    a = classify(p)
    assert a.kind == "protobuf"
    assert a.suggested_slot == "contracts/grpc"


def test_classify_unknown_returns_none(tmp_path: Path):
    p = tmp_path / "weird.xyz"
    p.write_text("???")
    a = classify(p)
    assert a.kind == "unknown"
    assert a.suggested_slot is None
