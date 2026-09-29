"""Zero-dependency providers used to validate the standalone boundary."""

from jarvis.contracts import ContextSnapshot, JarvisEvent


class StubMemory:
    def __init__(self) -> None:
        self.events: list[JarvisEvent] = []

    def remember(self, event: JarvisEvent) -> None:
        self.events.append(event)

    def context(self) -> ContextSnapshot:
        return ContextSnapshot(
            summary=f"{len(self.events)} local event(s)",
            metadata={"provider": "stub"},
        )


class StubCognition:
    def respond(self, user_input: str, context: ContextSnapshot) -> str:
        return f"JARVIS_V0: {user_input}"
