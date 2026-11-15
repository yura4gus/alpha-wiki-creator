"""Connection precedence without a network connection.

These tests never connect. They prove the factory address rules, that Cloud
auth comes from the Temporal SDK environment configuration, and that the API key
never reaches output.
"""

from __future__ import annotations

import json
import logging

import pytest
from temporalio.client import Client

from agent_factory.connection import (
    DEFAULT_ADDRESS,
    cloud_profile_configured,
    connect,
    connection_summary,
    env_config_configured,
    is_loopback,
    resolve_connect_config,
)

CLOUD_ADDRESS = "alpha-dev.n3kw9.tmprl.cloud:7233"
CLOUD_NAMESPACE = "alpha-dev.n3kw9"
API_KEY = "unit-test-api-key-never-print"


def profile_file(tmp_path, api_key: str = API_KEY, address: str = CLOUD_ADDRESS):
    path = tmp_path / "temporal.toml"
    path.write_text(
        "[profile.cloud]\n"
        f'address = "{address}"\n'
        f'namespace = "{CLOUD_NAMESPACE}"\n'
        f'api_key = "{api_key}"\n'
    )
    return path


def cloud_env(**extra: str) -> dict[str, str]:
    env = {
        "TEMPORAL_ADDRESS": CLOUD_ADDRESS,
        "TEMPORAL_NAMESPACE": CLOUD_NAMESPACE,
        "TEMPORAL_API_KEY": API_KEY,
    }
    env.update(extra)
    return env


def test_local_default_is_unchanged():
    assert resolve_connect_config(env={}) == {"target_host": DEFAULT_ADDRESS}


def test_factory_address_overrides_the_local_default():
    config = resolve_connect_config(env={"FACTORY_TEMPORAL_ADDRESS": "127.0.0.1:9999"})
    assert config == {"target_host": "127.0.0.1:9999"}
    assert "api_key" not in config and "tls" not in config


def test_cloud_profile_file_supplies_address_namespace_and_auth(tmp_path):
    config = resolve_connect_config(env={
        "TEMPORAL_CONFIG_FILE": str(profile_file(tmp_path)),
        "TEMPORAL_PROFILE": "cloud",
    })
    assert config["target_host"] == CLOUD_ADDRESS
    assert config["namespace"] == CLOUD_NAMESPACE
    assert config["api_key"] == API_KEY
    assert config["tls"] is True


def test_direct_temporal_env_supplies():
    config = resolve_connect_config(env={**cloud_env(), "TEMPORAL_TLS": "true"})
    assert config["target_host"] == CLOUD_ADDRESS
    assert config["namespace"] == CLOUD_NAMESPACE
    assert config["api_key"] == API_KEY
    assert config["tls"]


def test_explicit_argument_wins_and_keeps_cloud_auth(tmp_path):
    config = resolve_connect_config("override.example:1234", env={
        "TEMPORAL_CONFIG_FILE": str(profile_file(tmp_path)),
        "TEMPORAL_PROFILE": "cloud",
        "FACTORY_TEMPORAL_ADDRESS": "factory.internal:7233",
    })
    assert config["target_host"] == "override.example:1234"
    assert config["namespace"] == CLOUD_NAMESPACE
    assert config["api_key"] == API_KEY


@pytest.mark.parametrize("stale", ["localhost:7233", "127.0.0.1:7233", "[::1]:7233",
                                   "localhost:9999"])
def test_stale_loopback_factory_address_cannot_mask_cloud(stale):
    config = resolve_connect_config(env=cloud_env(FACTORY_TEMPORAL_ADDRESS=stale))
    assert config["target_host"] == CLOUD_ADDRESS


def test_api_key_alone_does_not_tls_a_local_factory_address():
    config = resolve_connect_config(env={
        "TEMPORAL_API_KEY": API_KEY,
        "FACTORY_TEMPORAL_ADDRESS": "localhost:7233",
    })
    assert config["target_host"] == "localhost:7233"
    assert "api_key" not in config and "tls" not in config


def test_cloud_profile_file_survives_a_stale_factory_address(tmp_path):
    config = resolve_connect_config(env={
        "TEMPORAL_CONFIG_FILE": str(profile_file(tmp_path)),
        "TEMPORAL_PROFILE": "cloud",
        "FACTORY_TEMPORAL_ADDRESS": "localhost:7233",
    })
    assert config["target_host"] == CLOUD_ADDRESS
    assert config["namespace"] == CLOUD_NAMESPACE
    assert config["api_key"] == API_KEY


def test_non_loopback_factory_address_still_outranks_env_config():
    config = resolve_connect_config(env=cloud_env(
        FACTORY_TEMPORAL_ADDRESS="factory.internal:7233"))
    assert config["target_host"] == "factory.internal:7233"
    assert config["namespace"] == CLOUD_NAMESPACE  # auth still comes from Cloud env


def test_explicit_argument_beats_the_factory_address_without_cloud():
    config = resolve_connect_config("argument:1111", env={
        "FACTORY_TEMPORAL_ADDRESS": "factory:2222"})
    assert config == {"target_host": "argument:1111"}


def test_loopback_detection_covers_cloud_hosts():
    for local in ("localhost:7233", "127.0.0.1:7233", "127.1.2.3:7233", "[::1]:7233",
                  "::1", "LOCALHOST:7233"):
        assert is_loopback(local)
    for remote in (CLOUD_ADDRESS, "factory.internal:7233", "10.0.0.1:7233"):
        assert not is_loopback(remote)


def test_env_triggers_are_precise():
    assert not env_config_configured(env={})
    assert not env_config_configured(env={"FACTORY_TEMPORAL_ADDRESS": "localhost:7233"})
    assert env_config_configured(env={"TEMPORAL_NAMESPACE": CLOUD_NAMESPACE})
    assert env_config_configured(env={"TEMPORAL_TLS": "false"})  # present opts in
    assert cloud_profile_configured(env={"TEMPORAL_API_KEY": API_KEY})
    assert not cloud_profile_configured(env={"TEMPORAL_TLS": "false"})
    assert cloud_profile_configured(env={"TEMPORAL_TLS": "true"})


def test_api_key_and_tls_are_read_but_never_printed(capsys, caplog):
    with caplog.at_level(logging.DEBUG):
        config = resolve_connect_config(env={**cloud_env(), "TEMPORAL_TLS": "true"})
        summary = connection_summary(config)
    assert config["api_key"] == API_KEY
    assert config["tls"]
    assert summary["api_key"] == "<redacted>"
    assert summary["target_host"] == CLOUD_ADDRESS
    out, err = capsys.readouterr()
    rendered = [repr(summary), json.dumps(summary, sort_keys=True), out, err, caplog.text]
    assert all(API_KEY not in text for text in rendered)


async def test_connect_defaults_to_localhost_without_config(monkeypatch):
    seen: dict = {}

    async def fake_connect(**kwargs):
        seen.update(kwargs)
        return object()

    monkeypatch.setattr(Client, "connect", fake_connect)
    for name in ("TEMPORAL_CONFIG_FILE", "TEMPORAL_PROFILE", "TEMPORAL_API_KEY",
                 "TEMPORAL_TLS", "TEMPORAL_NAMESPACE", "TEMPORAL_ADDRESS",
                 "FACTORY_TEMPORAL_ADDRESS"):
        monkeypatch.delenv(name, raising=False)

    await connect()

    assert seen == {"target_host": DEFAULT_ADDRESS}


async def test_connect_uses_resolution_without_printing_the_key(monkeypatch, capsys, caplog):
    seen: dict = {}

    async def fake_connect(**kwargs):
        seen.update(kwargs)
        return object()

    monkeypatch.setattr(Client, "connect", fake_connect)
    for name, value in cloud_env(FACTORY_TEMPORAL_ADDRESS="localhost:7233").items():
        monkeypatch.setenv(name, value)
    monkeypatch.delenv("TEMPORAL_CONFIG_FILE", raising=False)
    monkeypatch.delenv("TEMPORAL_PROFILE", raising=False)
    monkeypatch.delenv("TEMPORAL_TLS", raising=False)

    with caplog.at_level(logging.DEBUG):
        client = await connect()

    assert client is not None
    assert seen["target_host"] == CLOUD_ADDRESS
    assert seen["namespace"] == CLOUD_NAMESPACE
    assert seen["api_key"] == API_KEY
    assert seen["tls"]
    assert API_KEY not in capsys.readouterr().out
    assert API_KEY not in caplog.text
    assert "<redacted>" in caplog.text  # safe diagnostics exist
