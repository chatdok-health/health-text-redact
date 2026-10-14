"""Remove direct identifiers from English and German health conversation text."""

from .redact import Result, Span, redact

__all__ = ["Result", "Span", "redact"]
__version__ = "0.1.0"
