from collections import defaultdict
from typing import Any, Callable


class EventManager:
    def __init__(self) -> None:
        self._listeners: dict[str, list[Callable[..., Any]]] = defaultdict(list)

    def subscribe(self, event_type: str, listener: Callable[..., Any]) -> None:
        self._listeners[event_type].append(listener)

    def emit(self, event_type: str, **kwargs: Any) -> None:
        for listener in self._listeners[event_type]:
            listener(**kwargs)
