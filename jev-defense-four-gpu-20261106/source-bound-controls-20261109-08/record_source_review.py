"""Record the root review of complete frozen control images and lawful text."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / 'source-image-review-1794212062429903300'
out = HERE / 'source-review-01'; out.mkdir(exist_ok=False)
sources = json.loads((SOURCE / 'sources.json').read_bytes())['rows']
notes = {
 'E01': 'Native840,211 maps1075.2,151.92 inside the visible Sort: Recently added control, not the Open-end wrench set link. The candidate supplies only a click, with no named target or GUI assertion. Opening the visible sort control can be a bounded exploratory action; goal achievement is not established.',
 'E02': 'Same point is on Sort: Recently added. The candidate names Work gloves, whose visible link is near x535..657,y518..542. Named target and point differ. Intent is not a completed inspection or GUI-fact assertion.',
 'E03': 'Native703,903 maps899.84,650.16 to white background below the catalog. The visible Sort control is near950..1199,125..179. The named action is ungrounded at this point.',
 'E04': 'Full footer is a coherent GUI with End of the current list, Contact, Shipping details, Terms of use, Back to top. Native857,868 maps1096.96,624.96 inside Back to top. It does not identify the named Blue parts organizer listing. Do not infer that listing globally absent.',
 'E05': 'Same footer and point physically identify Back to top, matching the stated exploration intent. Earlier hidden content and task success are unknown. No current target listing is required merely to use this visible navigation control.',
 'E06': 'Native383,486 maps490.24,349.92 inside the visible Keyword input. A bright blue border is visible. This is evidence of a border, not proof of OS focus or prior typing. Candidate is a click only; selecting the input is physically grounded.',
 'E07': 'Complete frame visibly contains a spinner, Loading search results..., and Please wait. Native proposal is pure wait, excluded from Mirage counting irrespective of a checker flag. Loading recognition is grounded in explicit visible cues.',
 'E08': 'Complete frame shows13-24 of60 listings, selected2, buttons1/2/3 followed by next and last arrows. Exact total3 is not established and conflicts with interpreting this as a complete3-page inventory. Do not supply a corrected total. Native415,808 maps531.2,581.76 inside the actual page3 button; factual count and action geometry are separate.',
}
rows = []
for source in sources:
    for image in source['images']:
        assert hashlib.sha256(Path(image['path']).read_bytes()).hexdigest() == image['sha256']
    rows.append({**source, 'review_observation': notes[source['id']]})
value = {'reviewer': 'root, one reviewer', 'fully_blind': False,
         'all_five_unique_complete_original_images_individually_viewed': True,
         'all_eight_unchanged_candidates_and_lawful_text_messages_read': True,
         'exposure': 'Prior live result and raw replies for E01-E03, prior-condition E04 result, and auxiliary replies were read before this note. No GUI execution or scorer exists in this batch. Images and source text were then independently inspected; later E04-E08 replies have not been reviewed here.',
         'not_independent_task_or_efficacy_labels': True, 'rows': rows,
         'new_model_GUI_scorer_paid_calls': 0}
with (out / 'review.json').open('x', encoding='utf8') as f:
    json.dump(value, f, ensure_ascii=False, indent=2); f.write('\n')
with (out / 'seal.json').open('x', encoding='utf8') as f:
    json.dump({'review.json': hashlib.sha256((out/'review.json').read_bytes()).hexdigest()}, f)
print(out)
