"""New auxiliary prompt after a sealed repetition/cap failure; no budget change."""
from price_history_frame_binding import FRAME_RELATION,needs_price_history,check_price_history,task_text

FRAME_READ='''Read the ONE original screenshot (image index 0) independently of any actor.
Return one compact raw JSON object with all original screen fields:
status, visible, limitations, loading, evidence, reason.

In visible record EACH readable listing row ONCE, concisely:
readable title/identity | adjacent listing price | brief visible image content.
Keep rows separate. A price mentioned in description text is not the listing price.
For a partly cut-off row, record its readable fields and mark other fields unknown.
Do not guess a cut-off identity or price. Tiny clothing remains unknown when unreadable.
Do not omit readable price/title fields just because an image detail is unclear.
Do not repeat a row, its description, policy text or provenance in multiple entries.
Put distinct limitations briefly in limitations; reason is a brief explanation.

Every row needs an image citation in evidence:
{"observation_id":"actual supplied observation_id","image_index":0,
"coordinate_space":"pixels","box_xyxy":[left,top,right,bottom],
"description":"brief corresponding row evidence"}.
Use actual original pixel bounds without invented/clamped boxes.
The actual frame role is in provenance. With a current frame, status usable requires
readable facts and current-image evidence. With a reference-only frame, use limited
or unknown; readable facts remain PAST evidence only. Reference loading is uncertain.
Current loading is visible, not_observed or uncertain according to actual pixels.
No candidate, task answer, prior reports or hidden state are supplied. Do not infer
global absence, coverage, minimum, completed actions or current state from a past frame.
Do not give advice or actions. Include all required fields and end the JSON once.
'''
