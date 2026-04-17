from app.core.event_manager import EventManager


def test_subscribe_and_emit():
    em = EventManager()
    received = []
    em.subscribe("test.event", lambda **kw: received.append(kw))
    em.emit("test.event", foo="bar", baz=42)
    assert received == [{"foo": "bar", "baz": 42}]


def test_multiple_listeners_same_event():
    em = EventManager()
    calls = []
    em.subscribe("x", lambda **kw: calls.append("a"))
    em.subscribe("x", lambda **kw: calls.append("b"))
    em.emit("x")
    assert calls == ["a", "b"]


def test_no_listeners_no_error():
    em = EventManager()
    em.emit("ghost.event", data="nothing")


def test_different_events_isolated():
    em = EventManager()
    a_calls, b_calls = [], []
    em.subscribe("a", lambda **kw: a_calls.append(kw))
    em.subscribe("b", lambda **kw: b_calls.append(kw))
    em.emit("a", val=1)
    assert a_calls == [{"val": 1}]
    assert b_calls == []
