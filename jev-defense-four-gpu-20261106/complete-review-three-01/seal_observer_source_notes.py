import json, hashlib
from pathlib import Path
root=Path(__file__).parent/'observer-image-review-01'
manifest=json.loads((root/'source-manifest.json').read_text(encoding='utf-8'))
notes={
1:'Homepage: search form plus repeated listing cards; mixed composition. Keyword border not highlighted.',
2:'Homepage: same mixed form/list layout; Keyword field has blue focus border.',
3:'Homepage: same mixed form/list layout; basketball entered in blue-border Keyword field.',
4:'Search results, repeated listing rows and search sidebar; coherent legible interface.',
5:'Results list with sidebar; product thumbnail fine detail may be uncertain while interface text is readable.',
6:'Repeated listings; Rick Pitino book at $5 with man in dark suit visibly depicted; fine thumbnail text is separate.',
7:'Results-list bottom plus pagination/footer; page1 highlighted. Rick Pitino cover still visible.',
8:'Results top: 13-24 of50, sidebar and rows; coherent readable GUI.',
9:'Results rows; Victor $30 thumbnail visibly depicts man in green suit. This refutes universal no-suit, not $5 minimum.',
10:'Results rows and sidebar; small card/photo detail remains less certain than UI text.',
11:'Results bottom: globe, Bucknell listing, page2 highlighted, footer. Mixed lower-list/navigation region.',
12:'Results top:25-36 of50. Search sidebar and repeated rows.',
13:'Results rows: Kobe card, sports-card lot, memorabilia, partial Duke item. Tiny card content uncertain.',
14:'Results rows: JMU team photos, Sports Cards Lot, Harlem Globetrotters, Wii. Tiny JMU persons/clothing unresolved.',
15:'Results bottom: Wii/glove, page3 highlighted, footer. Mixed list/navigation region.',
16:'Results top:37-48 of50, search sidebar and repeated rows.',
17:'Repeated card-box/pendant rows; main visible structure is list, fine card faces not established.',
18:'Repeated product rows including watch, Nene, games and ball; list layout.',
19:'Results bottom: ball, wanted-card lot, page4 highlighted, footer. Mixed list/navigation region.',
20:'Results top:49-50 of50, two rows, sidebar and page5 highlighted pagination. No numeral1 visible; tiny montage contents unresolved.'}
rows=[]
for source in manifest['images_and_original_input_contract_only']:
    i=source['index']; sha=source['image_sha256']; image=root/'images'/f'{sha}.png'
    assert hashlib.sha256(image.read_bytes()).hexdigest()==sha
    layouts=['other','form','list_or_cards'] if i<=3 else (['list_or_cards','navigation_or_footer','other'] if i in (7,11,15,19) else ['list_or_cards'])
    rows.append({'index':i,'image_sha256':sha,'observation_id':source['observation_id'],
       'frame_appearance':'readable_gui','text_readability':'clear',
       'compatible_layouts':layouts,'visual_notes':notes[i],
       'scope':'Most visible UI text legible; no claim all tiny thumbnail content is readable; cropped/offscreen content is not absence.'})
review={'type':'source_first_visual_notes_before_observer_prediction_join','reviewer':'root',
 'count':len(rows),'all_original_images_viewed':True,'observer_replies_opened_before_seal':False,
 'limitations':['Single reviewer; source/current task/terminal facts already known. Not fully blind.',
 'Layout sets preserve mixed-layout ambiguity; not forced mutually exclusive gold.',
 'No new model/GUI/scorer calls. These notes are offline audit only.'],
 'source_manifest_sha256':hashlib.sha256((root/'source-manifest.json').read_bytes()).hexdigest(),'rows':rows}
target=root/'source-first-visual-review.json'
assert not target.exists()
target.write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
seal=root/'source-first-visual-seal.json'
assert not seal.exists()
seal.write_text(json.dumps({'files':{'source-first-visual-review.json':hashlib.sha256(target.read_bytes()).hexdigest(),
 'source-manifest.json':review['source_manifest_sha256'],Path(__file__).name:hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
 'prediction_join_not_yet_performed':True},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'review':str(target),'seal':str(seal),'seal_sha256':hashlib.sha256(seal.read_bytes()).hexdigest()},ensure_ascii=False))
