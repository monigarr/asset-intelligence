"""Orchestrator errors."""

from __future__ import annotations


class PipelineError(Exception):
    """Base class for inspection pipeline failures."""


class PipelineInputError(PipelineError):
    """Bad pipeline input: image count/type, note size/type, asset_meta shape."""
