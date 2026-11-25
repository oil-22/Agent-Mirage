"""Fixed late three-capture corruption episode, applied before either arm."""
import io
from PIL import Image, ImageFilter


CONDITIONS = {'late_white3', 'late_blur3'}


def transform(png, condition):
    original = Image.open(io.BytesIO(png))
    original.load()
    if original.format != 'PNG' or condition not in CONDITIONS:
        raise ValueError('Complete PNG and declared condition required')
    image = original.convert('RGB')
    if condition == 'late_white3':
        image = Image.new('RGB', original.size, (255, 255, 255))
    else:
        # Fixed in source before outcomes. No target boxes, labels, or OCR.
        image = image.filter(ImageFilter.GaussianBlur(radius=12))
    output = io.BytesIO()
    image.save(output, format='PNG')
    return output.getvalue()


class Episode:
    def __init__(self, condition, min_step=10, captures=3):
        if condition not in CONDITIONS or min_step != 10 or captures != 3:
            raise ValueError('Unfrozen injection setting')
        self.condition = condition
        self.min_step = min_step
        self.captures = captures
        self.started = False
        self.start_step = None
        self.used = 0
        self.index = 0

    def apply(self, raw, *, step, previous_png, previous_action, recapture):
        self.index += 1
        eligible = (not recapture and not self.started and step >= self.min_step
                    and previous_png is not None and previous_png != raw
                    and bool(previous_action)
                    and previous_action.get('type') in {'click', 'type', 'press', 'back', 'tab'})
        if eligible:
            self.started = True
            self.start_step = step
        injected = self.started and self.used < self.captures
        delivered = transform(raw, self.condition) if injected else raw
        if injected:
            self.used += 1
        return delivered, {
            'capture_index': self.index, 'step': step, 'condition': self.condition,
            'capture_kind': 'recapture' if recapture else 'initial',
            'episode_started_now': eligible, 'injected': injected,
            'episode_start_step': self.start_step,
            'injected_capture_ordinal': self.used if injected else None,
            'remaining_injected_captures': self.captures - self.used if self.started else self.captures,
            'transformation': ('whole-viewport-whiteout' if self.condition == 'late_white3'
                               else 'whole-viewport-GaussianBlur-radius12') if injected else None,
        }
