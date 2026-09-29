"""Adapter seam for an independently running Personal Jarvis instance.

J1 deliberately does not import Personal Jarvis internals. The donor remains
replaceable and may be installed/updated independently.

The transport is injectable so unit tests require neither network nor donor
installation. A concrete HTTP/WebSocket transport is added only after the
upstream public API surface is verified.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from jarvis.contracts import ContextSnapshot


class PersonalJarvisTransport(Protocol):
    def chat(self, text: str, context: ContextSnapshot) -> str: ...


@dataclass
class PersonalJarvisCognition:
    transport: PersonalJarvisTransport

    def respond(self, user_input: str, context: ContextSnapshot) -> str:
        if not user_input.strip():
            raise ValueError("user_input must not be empty")
        return self.transport.chat(user_input, context)
