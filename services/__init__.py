"""Trend-fetching services for the Trend Radar MCP server.

Each module exposes plain functions that return ``list[TrendItem]`` and raise
``ServiceError`` on failure, so the MCP layer (server.py) and the dashboard
generator (services/dashboard.py) can consume them uniformly.
"""
