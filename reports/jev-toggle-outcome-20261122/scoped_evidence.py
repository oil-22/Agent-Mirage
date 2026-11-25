"""Bind scope and decide when to ask; the evidence here cannot authorize delivery."""

import io
import math

from PIL import Image

from live_common import canonical, hash_bytes
from temporal_request import action_json
from toggle_protocol import DISPATCH, eligible, probe, record_scope, unpack


def anchor(binding, action, evidence, old, old_packet):
    claim = unpack(binding, evidence)
    if not claim or action.get('type')!='click' or (claim.get('protocol'), claim.get('action_sequence'), claim.get('action'))!=(DISPATCH,1,action):
        return 'unverifiable_click'
    try:
        action_json(action)
    except ValueError:
        return 'unverifiable_click'
    dims=binding['viewport']
    xy=claim.get('pointer')
    expected=[action['x']*dims[0]/1000,action['y']*dims[1]/1000]
    if not isinstance(xy,list) or len(xy)!=2 or any(type(x) not in (float,int) or not math.isfinite(x) or abs(x-y)>.001 for x,y in zip(xy,expected)):
        return 'unverifiable_click'
    live=probe(binding,old,old_packet,0)
    if not live or live[0]!=xy:
        return 'unverifiable_click'
    sent, seen=claim['hit'],live[1]
    if sent is None and seen is None:
        return 'plain_click'
    if record_scope(sent,xy,dims) and record_scope(seen,xy,dims) and (sent['node'],sent['kind'])==(seen['node'],seen['kind']):
        return 'bound_toggle'
    return 'unverifiable_click'


def assess(binding, action, dispatch, frames, probes):
    """Require stability at the actual target plus its tightly bounded feedback area."""
    outline=eligible(binding, action, dispatch, frames, probes, require_target_change=False)
    if not outline['eligible']:
        return outline
    w,h=binding['viewport']
    x,y,r,b=outline['comparison_box']
    # Inspect pixels only to decide whether to ask; no crop or state is sent
    # to Flash. Exclude the neighbor at the same height and distant banners.
    strips=[[x,y,r,b],[max(0,x-2),min(h,b+3),min(w,max(r,x+620)),min(h,b+62)]]
    if strips[1][3]<=strips[1][1]:
        strips.pop()
    context=[]
    for f in frames:
        with Image.open(io.BytesIO(f.png)) as im:
            if im.size!=(w,h) or im.format!='PNG' or im.n_frames!=1:
                return {'eligible':False,'reason':'not_a_full_original_png'}
            rgb=im.convert('RGB')
            context.append(hash_bytes(canonical(strips)+b''.join(rgb.crop(rect).tobytes() for rect in strips)))
    one,two,three=context
    reason=('local_pixels_still_changing' if two!=three else 'no_local_visual_change' if one==three else 'ask_about_clicked_control')
    return {**outline,'eligible':reason=='ask_about_clicked_control','reason':reason,'checked_regions':strips,
            'before_and_two_latest_region_hashes':context}
