"""Portable image intervention functions for the offline attention study."""
from io import BytesIO
from math import ceil, floor

from PIL import Image


def intervene(current, condition, *, previous=None, control_boxes=None):
    """Return full PNG bytes, or None (the caller omits the image block). Coordinates: [0,1000]."""
    if condition == "current_control":
        return current
    if condition == "silent_drop":
        return None
    if condition == "stale_replace":
        if previous is None:
            raise ValueError("An actual previous screenshot is required")
        return previous
    if condition not in {"buttons_only", "blank_replace"}:
        raise ValueError("Unknown condition")
    with Image.open(BytesIO(current)) as source:
        original = source.convert("RGB")
    w, h = original.size
    frame = Image.new("RGB", original.size, "white")
    if condition == "buttons_only":
        if control_boxes is None:
            raise ValueError("Provide the annotated control rectangles")
        for x0,y0,x1,y1 in control_boxes:
            if not (0 <= x0 < x1 <= 1000 and 0 <= y0 < y1 <= 1000):
                raise ValueError("Invalid normalized rectangle")
            box = (floor(x0*w/1000),floor(y0*h/1000),ceil(x1*w/1000),ceil(y1*h/1000))
            frame.paste(original.crop(box), box)
    buf = BytesIO()
    frame.save(buf,format="PNG")
    return buf.getvalue()
