import tkinter as tk

class Debouncer:
    def __init__(self, widget: tk.Widget, wait_ms: int, callback: callable):
        """
        Generic Tkinter-based debouncer.

        Args:
            widget: A tkinter widget to use for .after() and .after_cancel().
            wait_ms: Delay in milliseconds.
            callback: Function to execute after the delay.
        """
        self.widget = widget
        self.wait_ms = wait_ms
        self.callback = callback
        self.timer_id = None

    def schedule(self, *args):
        """Schedules or resets the debounce timer."""
        if self.timer_id:
            self.widget.after_cancel(self.timer_id)
        self.timer_id = self.widget.after(self.wait_ms, self.callback)
