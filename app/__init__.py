"""Application package entrypoint.

The historical monolithic implementation lives in ``legacy.py`` while the
package entrypoint stays intentionally small. Cross-cutting HTTP security is
attached here so route modules do not need to know about infrastructure.
"""

from .legacy import *  # noqa: F401,F403
from .legacy import app, db
from .bootstrap import configure_security

configure_security(app)

__all__ = ["app", "db"]
