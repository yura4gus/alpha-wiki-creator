"""One conflict-safe Temporal connection for the factory, local or Cloud.

Address precedence:

1. the explicit ``address`` argument (CLI ``--address`` override);
2. ``FACTORY_TEMPORAL_ADDRESS``, unless it is a stale loopback value while a
   Cloud profile is configured;
3. the Temporal SDK environment configuration
   (``TEMPORAL_CONFIG_FILE`` / ``TEMPORAL_PROFILE`` / ``TEMPORAL_API_KEY`` /
   ``TEMPORAL_TLS`` / ``TEMPORAL_NAMESPACE``, including ``TEMPORAL_ADDRESS``);
4. ``localhost:7233``.

Whenever one of the listed ``TEMPORAL_*`` variables is present, the SDK's
``ClientConfig.load_client_connect_config()`` supplies the namespace, API key,
TLS and RPC metadata. Callers therefore never hand-assemble Cloud auth.

The API key exists only in the connect mapping handed to the Temporal SDK. It
is never logged, placed in workflow input/history, or written to a receipt.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Mapping

from temporalio.client import Client
from temporalio.envconfig import ClientConfig

DEFAULT_ADDRESS = "localhost:7233"

logger = logging.getLogger(__name__)

# The SDK loader also reads TEMPORAL_ADDRESS; these are the variables that make
# a factory process opt into environment configuration at all.
_ENV_TRIGGERS = (
    "TEMPORAL_CONFIG_FILE",
    "TEMPORAL_PROFILE",
    "TEMPORAL_API_KEY",
    "TEMPORAL_NAMESPACE",
)

# Signals that the environment describes a Cloud profile rather than a local
# dev server. A loopback FACTORY_TEMPORAL_ADDRESS must not mask these.
_CLOUD_FIELDS = (
    "TEMPORAL_CONFIG_FILE",
    "TEMPORAL_PROFILE",
    "TEMPORAL_API_KEY",
    "TEMPORAL_NAMESPACE",
)


def _environment(env: Mapping[str, str] | None) -> Mapping[str, str]:
    return os.environ if env is None else env


def env_config_configured(env: Mapping[str, str] | None = None) -> bool:
    """True when the SDK env config should be loaded for this process."""
    current = _environment(env)
    if any(current.get(name) for name in _ENV_TRIGGERS):
        return True
    return "TEMPORAL_TLS" in current


def cloud_profile_configured(env: Mapping[str, str] | None = None) -> bool:
    """True when the environment configures Cloud auth or a Cloud profile."""
    current = _environment(env)
    if any(current.get(name) for name in _CLOUD_FIELDS):
        return True
    return _truthy(current.get("TEMPORAL_TLS"))


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _host(address: str) -> str:
    value = address.strip()
    if value.startswith("[") and "]" in value:  # [::1]:7233 or [::1]
        return value[1:value.index("]")].lower()
    if value.count(":") > 1:  # bare IPv6 has no unambiguous port
        return value.strip("[]").lower()
    host, separator, port = value.rpartition(":")
    if separator and port.isdigit():
        return host.lower()
    return value.lower()


def is_loopback(address: str) -> bool:
    """True for localhost / IPv4 loopback / IPv6 loopback, with or without port."""
    host = _host(address)
    return host in {"localhost", "::1"} or host.startswith("127.")


def resolve_connect_config(
    address: str | None = None, *, env: Mapping[str, str] | None = None
) -> dict[str, Any]:
    """Build keyword arguments for ``Client.connect`` without connecting.

    ``env`` is injectable so the precedence rules can be tested without a
    network or process-global environment mutation.
    """
    current = _environment(env)
    config: dict[str, Any] = {}
    if env_config_configured(current):
        config.update(
            ClientConfig.load_client_connect_config(override_env_vars=dict(current))
        )

    explicit_address = (address or "").strip() or None
    factory_address = (current.get("FACTORY_TEMPORAL_ADDRESS") or "").strip() or None
    env_target = str(config.get("target_host") or "").strip() or None
    # A Cloud profile with a real remote endpoint outranks a stale loopback factory
    # default. A lone API key (no Cloud address) does not: it must not turn a deliberately
    # local worker/test into a TLS connection to localhost.
    if (
        factory_address
        and not explicit_address
        and cloud_profile_configured(current)
        and is_loopback(factory_address)
        and env_target
        and not is_loopback(env_target)
    ):
        factory_address = None

    target = explicit_address or factory_address or env_target
    if not target:
        target = DEFAULT_ADDRESS
    config["target_host"] = target
    if is_loopback(target):
        # Loopback is the local dev server: plaintext, no Cloud credential or mTLS.
        for key in ("api_key", "tls", "rpc_metadata"):
            config.pop(key, None)
    return config


def connection_summary(config: Mapping[str, Any]) -> dict[str, Any]:
    """Redacted connection facts safe to log. Never returns the API key."""
    return {
        "target_host": config.get("target_host", DEFAULT_ADDRESS),
        "namespace": config.get("namespace", "default"),
        "tls": bool(config.get("tls")),
        "api_key": "<redacted>" if config.get("api_key") else None,
    }


async def connect(address: str | None = None) -> Client:
    """Connect to Temporal using factory precedence plus SDK Cloud config."""
    config = resolve_connect_config(address)
    logger.debug("Temporal connection: %s", connection_summary(config))
    return await Client.connect(**config)
