import re

def generate_clone_title(original_title: str) -> str:
    """
    Generates a new title for a cloned item.
    - If title ends in ' (Clone)', appends ' 1'.
    - If title ends in ' (Clone X)', increments X.
    - Otherwise, appends ' (Clone)'.
    """
    # Check for ' (Clone X)' at the end
    match = re.search(r' \(Clone (\d+)\)$', original_title)
    if match:
        number = int(match.group(1))
        base = original_title[:match.start()]
        return f"{base} (Clone {number + 1})"
    
    # Check for ' (Clone)' at the end
    if original_title.endswith(' (Clone)'):
        return f"{original_title[:-8]} (Clone 1)"
    
    return f"{original_title} (Clone)"
