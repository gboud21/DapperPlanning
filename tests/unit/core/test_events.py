import pytest
from unittest.mock import MagicMock
from dataclasses import dataclass
from src.core.events import EventDispatcher, Event

# Dummy event for testing, inherits from Event base class
@dataclass
class DummyEvent(Event):
    message: str

def test_event_subscription_and_dispatch():
    """Verifies that a subscriber receives the correct event payload."""
    # EventDispatcher requires a root window (tk.Tk)
    root = MagicMock()
    dispatcher = EventDispatcher(root)
    received_events = []
    
    def handle_dummy_event(event: DummyEvent):
        received_events.append(event.message)
        
    dispatcher.subscribe(DummyEvent, handle_dummy_event)
    dispatcher.dispatch(DummyEvent(message="Hello World"))
    
    assert len(received_events) == 1
    assert received_events[0] == "Hello World"

def test_unsubscribe():
    """Verifies that un-subscribing prevents further event reception."""
    root = MagicMock()
    dispatcher = EventDispatcher(root)
    received_events = []
    
    def handle_dummy_event(event: DummyEvent):
        received_events.append(event)
        
    dispatcher.subscribe(DummyEvent, handle_dummy_event)
    dispatcher.unsubscribe(DummyEvent, handle_dummy_event)
    dispatcher.dispatch(DummyEvent(message="Ghost Message"))
    
    assert len(received_events) == 0
