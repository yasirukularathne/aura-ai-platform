import logging
from collections.abc import Mapping
from contextlib import contextmanager
from time import perf_counter

from app.config import settings

logger = logging.getLogger("aura.observability")


@contextmanager
def trace(name: str, metadata: Mapping[str, object] | None = None):
    """Create a Langfuse generation span when configured, otherwise log timing."""
    started = perf_counter()
    langfuse = None
    if settings.langfuse_public_key and settings.langfuse_secret_key:
        try:
            from langfuse import Langfuse

            langfuse = Langfuse(
                public_key=settings.langfuse_public_key,
                secret_key=settings.langfuse_secret_key,
                host=settings.langfuse_host,
            )
        except ImportError:
            logger.warning("langfuse_not_installed")
    try:
        yield
    finally:
        duration_ms = (perf_counter() - started) * 1000
        logger.info(
            "trace_complete",
            extra={"trace_name": name, "duration_ms": round(duration_ms, 3), **(metadata or {})},
        )
        if langfuse is not None:
            langfuse.flush()
