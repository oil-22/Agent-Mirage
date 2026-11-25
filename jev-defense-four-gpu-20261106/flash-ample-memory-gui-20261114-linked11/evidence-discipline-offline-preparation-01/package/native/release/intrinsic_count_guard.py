"""Withhold an internally impossible literal range; supply no corrected reading."""
import re

RANGE=re.compile(r'(?<!\d)(\d+)\s*[-–—]\s*(\d+)\s+of\s+(\d+)\s+(?:listings?|results?|items?)\b',re.I)

def check_intrinsic_counts(reading):
    conflicts=[]
    for index,row in enumerate(reading['text_spans']):
        for match in RANGE.finditer(row['text']):
            start,end,total=map(int,match.groups())
            if start>end or end>total:
                conflicts.append({'text_index':index,'text_id':row['id'],'exact_span':match.group(),
                                  'reason':'literal_start_end_total_internally_inconsistent'})
    return {'reject':bool(conflicts),'conflicts':conflicts,'image_truth_certified':False,
            'reading_modified':False,'corrected_digits_or_action_supplied':False,
            'unflagged_is_not_approval':True}
