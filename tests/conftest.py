"""Shared pytest configuration.

The test suite runs against the PostgreSQL database provisioned by CI. Query
unit tests use mocks and do not need a temporary application context.
"""
