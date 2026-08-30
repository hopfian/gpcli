"""Process-wide CLI context (populated by the main callback, read by commands).

Lives outside `main.py` so commands can import it without circularity.
The `client()` factory is the single sanctioned way for presentation code
to obtain an API client — commands never construct `MyGPClient` (or touch
`httpx`) directly (Dependency Inversion).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field

from gpcli.client import MyGPClient
from gpcli.state import State, load_state


@dataclass
class Context:
    json_out: bool = False
    state: State = field(default_factory=load_state)

    @contextmanager
    def client(self) -> Iterator[MyGPClient]:
        """Yield a pooled client bound to this context's state; always closed."""
        client = MyGPClient(self.state)
        try:
            yield client
        finally:
            client.close()


_context: Context | None = None


def get_context() -> Context:
    global _context
    if _context is None:
        _context = Context()
    return _context


def set_context(ctx: Context) -> None:
    global _context
    _context = ctx
