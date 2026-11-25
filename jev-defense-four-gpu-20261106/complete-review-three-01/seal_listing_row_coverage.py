"""Offline original-pixel row inventory; not a clothing gold or checker input."""
import json,hashlib
from pathlib import Path
root=Path(__file__).parent
manifest=json.loads((root/'observer-image-review-01/source-manifest.json').read_bytes())
source={r['index']:r for r in manifest['images_and_original_input_contract_only']}
items=[
(1,4,'Early Jason Kidd Basketball Cards'),(1,4,'Rocks/Boulders'),(1,4,'iTouch Air3 smart watch'),
(1,5,'Sports Cards and Memorabilia at Flea Market'),(1,5,'Mixed Sports Cards lot, RPA, Auto, Rookies, Graded Football Basketball'),(1,5,'545 Different Sports Illustrated magazines'),(1,5,'Super Nintendo Games - NBA Jam, NFL Madden & More'),
(1,6,'Wanted: All Baseball, Football, Sports Cards Collections'),(1,6,'Jewelry, Coins, Sport Cards And Memorabilia'),(1,6,'1994 McDonalds Michael Jordan Nothing But Net15 card set'),(1,6,'Success is a Choice by Rick Pitino'),(1,7,"5,400+ BASKETBALL ROOKIE CARDS FROM THE1990s"),
(2,8,'2023-24 Virginia Basketball Complete Team Signed Full Size Poster'),(2,8,'1986-87 Fleer #57 Jordan Rookie'),(2,8,'Michael Jordan Signed Basketball W/ COA'),
(2,9,'Victor Wembanyama Rookie Basketball Card'),(2,9,'Last chance sofa foosball bar chair'),(2,9,'Buying Baseball football autograph and vintage SPORTS CARDS'),(2,9,'30 cards for$22 FOOTBALL BASKETBALL baseball hockey non sport CARDS'),
(2,10,'Basketball Trash Can'),(2,10,'1992 Barcelona Olympics Pins'),(2,10,'Buying Sports Cards & Collectibles'),(2,10,'GLOBE IN STAND'),(2,11,'Bucknell university mini basketball binders and coozie'),
(3,12,'Vintage Getty basketball glasses'),(3,12,'Space Jam2 Basketball'),(3,12,'17 Box EMPTY Flawless Basketball Cards Briefcase Immaculate, The Cup'),
(3,13,'Kobe Bryant-2001 SP Authentic Game Used NBA Floor Card'),(3,13,'BASEBALL FOOTBALL BASKETBALL HOCKEY cards$100 each'),(3,13,'Sports memorabilia sale football basketball autographs'),(3,13,'Duke University basketball yearbooks and magazines1990-early2000s'),
(3,14,'JMU Basketball Team Photos Lefty Driesell/Team Signatures'),(3,14,'Sports Cards Lot'),(3,14,'Harlem Globetrotters program'),(3,14,'Nintendo Wii Video Game Bundle'),(3,15,'Vintage1950s Leather SONNETT FLEXOTAN BASEBALL GLOVE J4F'),
(4,16,'LEN BIAS UNIVERSITY OF MD TERPS TERRAPINS POSTER'),(4,16,'Baseball,Football,Hockey, Basketball vintage cards'),(4,16,'dr seuss wall clock'),
(4,17,'1990-91 NBA Hoops Basketball Cards Sealed Box Ewing-Robinson on cover'),(4,17,'1990-91 NBA Basketball SKYBOX Factory Sealed Robinson & Akeen on cover'),(4,17,'1990-91 NBA Basketball SKYBOX Factory Sealed Jordan & Bird on cover'),(4,17,'Sterling silver basketball pendant/charm'),
(4,18,'MICHAEL JORDAN Limited Edition Wristwatch in Special BASKETBALL Case'),(4,18,'Nene Wizards bobblehead'),(4,18,'Super Nintendo Games - NBA Jam, NFL Madden & More'),(4,18,'University of Kentucky wildcats mini basketball New'),(4,19,'Wanted: All Baseball, Football, Sports Cards Collections'),
(5,20,'Sports Illustrated - The Basketball Book'),(5,20,'545 Different Sports Illustrated magazines')]
assert len(items)==50
rows=[]
for n,(page,im,title)in enumerate(items,1):
 s=source[im];rows.append({'search_row_ordinal':n,'page_in_observed_navigation':page,'image_index_in20':im,'image_sha256':s['image_sha256'],'observation_id':s['observation_id'],'readable_row_title_anchor':title})
out={'reviewer':'root','row_count':50,'all_original20_GUI_images_viewed':True,
 'page_row_counts':{'1':12,'2':12,'3':12,'4':12,'5':2},
 'title_anchor_normalization':'Offline readable anchors, spacing/punctuation abbreviated; original image bytes are authoritative.',
 'scope':'Every result row appears in actual delivered frames. Some rows appear across overlapping frames. Repeated titles on different result pages are separate displayed rows, not proof of distinct items. This is not proof every tiny depicted garment was resolved, or proof of global minimum.',
 'no_model_GUI_calls':True,'not_model_or_checker_input':True,'rows':rows}
p=root/'listing-row-coverage-root.json';assert not p.exists();p.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
s=root/'listing-row-coverage-root-seal.json';assert not s.exists();s.write_text(json.dumps({'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest(),Path(__file__).name:hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}},indent=2)+'\n',encoding='utf-8')
print(json.dumps({'count':len(rows),'seal_sha256':hashlib.sha256(s.read_bytes()).hexdigest()}))
