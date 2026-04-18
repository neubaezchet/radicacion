"""Almacenamiento en memoria de jobs de radicación (sustituible por Redis/BD)."""

from typing import Any

radicaciones: dict[str, dict[str, Any]] = {}
