"""Optional use of the operating system's certificate store for outgoing HTTPS.

Python normally verifies HTTPS certificates against its own bundle (certifi). On machines where
antivirus software inspects HTTPS traffic (e.g. Avast Web Shield re-signs it with its own root
certificate, trusted only by Windows), downloads of the NLP models from Hugging Face then fail.
Setting ``USE_SYSTEM_CERTS=true`` makes Python verify against the OS store instead, exactly as
pip does. It trusts nothing the operating system does not already trust.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)
_injected = False


def use_system_certificates() -> None:
    """Verify HTTPS against the OS certificate store (idempotent)."""
    global _injected
    if _injected:
        return
    import truststore

    truststore.inject_into_ssl()
    _injected = True
    logger.info("HTTPS certificates are verified against the operating system store.")
