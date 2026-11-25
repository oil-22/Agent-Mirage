"""Task-independent content-column white mask, fixed before model outcomes.

This is a distinct development condition. It never synthesizes a normal frame.
The browser remains live and every capture retains its untouched original PNG.
"""
import io
from PIL import Image, ImageDraw


CONDITIONS = {'late_content_mask3'}


def transform(png, condition):
    original = Image.open(io.BytesIO(png))
    original.load()
    if original.format != 'PNG' or condition not in CONDITIONS:
        raise ValueError('Full PNG and frozen condition required')
    image = original.convert('RGB')
    # Fixed screen fractions, without task-specific targets, OCR, or labels.
    x0 = original.width * 3 // 10
    y0 = original.height * 17 // 100
    ImageDraw.Draw(image).rectangle((x0, y0, original.width-1, original.height-1), fill=(255, 255, 255))
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
            'remaining_injected_captures': self.captures-self.used if self.started else self.captures,
            'transformation': 'content-column-white-mask-x30pct-y17pct' if injected else None,
        }
