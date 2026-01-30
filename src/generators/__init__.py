"""
VETKA Generators module - Demo data and sample generation.

Provides utilities for generating sample workflow data for testing
and demonstration purposes.

@status: active
@phase: 96
@depends: sample_data
@used_by: tests, demo scripts
"""

from .sample_data import SampleDataGenerator

__all__ = ["SampleDataGenerator"]
