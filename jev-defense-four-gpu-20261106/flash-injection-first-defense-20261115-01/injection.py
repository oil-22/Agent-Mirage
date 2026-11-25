"""Source-bound, once-only visual whiteout; no task answers or detector labels."""
import io
from PIL import Image


def whiteout(png):
    original = Image.open(io.BytesIO(png))
    original.load()
    if original.format != 'PNG':
        raise ValueError('A complete original PNG is required')
    output = io.BytesIO()
    Image.new('RGB', original.size, (255, 255, 255)).save(output, format='PNG')
    return output.getvalue()


def eligible(fired, previous_png, current_png, previous_action):
    return (not fired and previous_png is not None and previous_png != current_png
            and bool(previous_action)
            and previous_action.get('type') in {'click', 'type', 'press', 'back', 'tab'})
