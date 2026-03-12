"""Zeebe/Camunda connection configuration."""

from __future__ import annotations

import os

from pydantic import BaseModel, field_validator


class ZeebeConfig(BaseModel):
    """Connection settings for Zeebe and Camunda services.

    Use ``from_env()`` to load from environment variables.
    """

    zeebe_grpc: str = "localhost:26500"
    zeebe_rest: str = "http://localhost:8088"
    camunda_operate_url: str = "http://localhost:8088"

    @field_validator("zeebe_grpc")
    @classmethod
    def _validate_grpc_address(cls, v: str) -> str:
        if not v:
            raise ValueError("zeebe_grpc must not be empty")
        if v.startswith(("http://", "https://")):
            raise ValueError(
                "zeebe_grpc must be host:port without scheme, got: " + v
            )
        return v

    @field_validator("zeebe_rest", "camunda_operate_url")
    @classmethod
    def _validate_http_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("must start with http:// or https://, got: " + v)
        return v

    @classmethod
    def from_env(cls) -> ZeebeConfig:
        """Create config from environment variables with defaults."""
        kwargs: dict[str, str] = {}
        env_map = {
            "ZEEBE_GRPC": "zeebe_grpc",
            "ZEEBE_REST": "zeebe_rest",
            "CAMUNDA_OPERATE_URL": "camunda_operate_url",
        }
        for env_key, field_name in env_map.items():
            val = os.environ.get(env_key)
            if val is not None:
                kwargs[field_name] = val
        return cls(**kwargs)
