"""Chainlit integration lives in the top-level chainlit_app package.

The runtime entrypoint remains `chainlit_app/main.py` because Chainlit loads
files by path. That UI delegates to `/api/query`, which uses the AgentRouter.
"""

