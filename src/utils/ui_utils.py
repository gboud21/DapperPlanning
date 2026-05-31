import tkinter as tk

def enable_scroll_bubbling(child_widget: tk.Widget, parent_canvas: tk.Canvas):
    """
    Enables 'Scroll Bubbling' for greedy widgets like Text and Listbox.
    When the child widget reaches its scroll limit, mouse wheel events are
    forwarded to the parent canvas.
    """
    def _on_mousewheel(event):
        # Determine scroll direction
        # Linux uses event.num (4 for up, 5 for down)
        # Windows/Mac use event.delta (positive for up, negative for down)
        if event.num == 4 or event.delta > 0:
            direction = -1  # Scroll Up
        elif event.num == 5 or event.delta < 0:
            direction = 1   # Scroll Down
        else:
            return

        # Check scroll limits of the child widget
        # yview() returns (top, bottom) as fractions (0.0 to 1.0)
        top, bottom = child_widget.yview()

        if (direction == -1 and top <= 0.0) or (direction == 1 and bottom >= 1.0):
            # At limit: forward scroll to parent canvas
            parent_canvas.yview_scroll(direction, "units")
            return "break"
        
        # Not at limit: let the child widget handle the scroll naturally
        return None

    # Bind for Windows/macOS and Linux
    child_widget.bind("<MouseWheel>", _on_mousewheel)
    child_widget.bind("<Button-4>", _on_mousewheel)
    child_widget.bind("<Button-5>", _on_mousewheel)
