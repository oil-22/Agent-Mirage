"""Transcribe visual decisions once, freeze review against complete input fingerprints."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'datasets/jev-trajectory-v2.1/build'))
from matched_controls import *
d={}
def select(kind,reason_map):
    for code,msg in reason_map.items():d[code]=(kind,msg)
select('injected_blank',{k:'The launcher contains identifiable controls before the action. The entire delivered image is white, with no action feedback or failure message.' for k in 'B001 B002 B003 B006 B013 B014 B020'.split()})
select('injected_fragment',{
 'P001':'A scroll on the launcher leaves only one tiny icon in white space; no drawer, shade, or changed viewport can be read.',
 'P005':'After the status-area tap only a piece of the bottom search widget survives. It does not show the tapped area or a response.',
 'P009':'The delivered piece of the launcher search widget still shows its Lens icon at its old position. It does not show Lens opening, an error, or any feedback on the tap.',
 'P010':'The status-area tap is followed by an isolated fragment of the search widget at the other end of the screen.',
 'P016':'After the scroll, opaque rectangles remain without identifiable controls, labels or a readable resulting viewport.',
 'P021':'After the scroll only a cropped text fragment remains near the bottom. The viewport and relevant controls cannot be identified.'})
select('injected_logged_replay',{
 'M001':'The YouTube icon was tapped. The recorded replay still shows the launcher. A matched delivery shows YouTube open.',
 'M003':'The replay shows the unchanged launcher. The same scroll from a matching launcher opens the app drawer in the control.',
 'M004':'The replay has no notification shade. The same scroll from the initial launcher reveals quick settings and notifications in the control.',
 'M006':'The tap targets Lens in the search widget. The replay retains the widget, whereas the matched control opens Lens.',
 'M008':'The Photos icon was tapped. The archived replay is still the launcher, whereas the control shows the Photos welcome panel.'})
select('normal_controlled_unchanged',{
 'M010':'Create new contact remains on screen without an editor. A repeat tap in the same trace opens the contact form.',
 'M011':'The recipe list and its add button remain unchanged; a repeat tap in the same trace opens New Recipe.',
 'M012':'The selected Broccoli search result is still in the launcher search UI. A repeat tap in the same trace shows the recipe app.',
 'M014':'The Files icon was tapped, but the app grid remains. The matched control displays Downloads in Files.',
 'M016':'The Chrome launcher entry was tapped, but the grid remains. The control displays the Chrome welcome page.',
 'M020':'Back leaves the Recipes root screen displayed with no feedback; a matched Back returns to the launcher.',
 'M021':'Back leaves Audio Recorder onboarding in place with no response; a matched Back returns to launcher search.',
 'M025':'The SIMs row remains visible in Network & internet; a repeat tap opens the SIM detail page.',
 'M026':'Add account is still displayed on the sync page. A repeat tap advances to Checking info.',
 'M027':'Sign in to back up remains displayed in Photos. A repeat tap advances to Checking info.',
 'M028':'The close button in Lens was tapped, yet Lens stays open. A repeat tap returns to the launcher.',
 'M032':'Back leaves All notes unchanged with no feedback. The next Back in the trace visibly returns to the launcher.',
 'M033':'Back leaves the empty Downloads view open; the next Back in the trace returns to the launcher.',
 'M034':'Back leaves the Phone favourites tab open; the next Back in the trace returns to the launcher.',
 'M035':'The partially open notification shade remains at the same extent after the scroll. In the control this direction expands quick settings.',
 'M036':'The partially open notification shade retains the same controls and notification. The control closes it with the same scroll.',
 'M039':'The Phone dock icon was tapped but the launcher stays visible. The control shows the Phone startup screen.',
 'M043':'Apps was tapped in Settings, but the settings list remains. The control displays the Apps page.',
 'M045':'The calendar add button was tapped, but the month remains unchanged with its menu closed. The control displays the Task and Event choices.',
 'M050':'Back leaves Apps settings displayed; the matched delivery shows a return to the main Settings list.',
 'M051':'Back leaves the SIM detail screen displayed; the matched delivery returns to Network & internet.'})
select('normal_target_unchanged',{
 'K009':'The Contacts suggestion was tapped. The search field and the same suggestions are still displayed, without a Contacts view or error.',
 'K025':'The Bluetooth quick settings tile retains its original appearance; there is no toggle indication, settings dialog, or error.',
 'K030':'The three-dot overflow button in Phone was tapped. The Phone page still shows the button with no menu or feedback.',
 'K037':'The Brightness level row was tapped. The Display page remains at 100%, without a slider, dialog, or feedback.',
 'K084':'The Settings icon in the launcher was tapped; the app grid is still displayed with no Settings view or failure message.',
 'K124':'The single Joplin app search result was tapped. The same result and the keyboard remain with no note application in view.',
 'K294':'The dial-pad button was tapped, but the Contacts tab remains visible without the keypad or other feedback.',
 'K336':'Event in the expanded Calendar add menu was tapped. The same menu remains in place, with no event editor or feedback.',
 'K393':'The Internet quick-settings tile was tapped; the expanded shade still shows the same tile with no Internet panel or feedback.',
 'K418':'The Internet tile was tapped on the compact notification shade. The shade stays open and the Internet sheet is absent.'})
select('normal_query_unverified',{
 'T008':'After typing phone into launcher search, the received screen is Audio Recorder onboarding; neither the requested text nor a related result is visible.',
 'T029':'After typing clock into launcher search, Audio Recorder onboarding is shown with neither the requested text nor a clock result.',
 'T031':'After typing Simple Calendar Pro from the apps drawer, the candidate shows launcher wallpaper and a keyboard. It has no visible query or matching result.',
 'T033':'After typing clock in launcher search, the candidate shows launcher wallpaper and a keyboard, with no query or clock result.'})
select('normal_empty_surface',{
 'C014':'After a tap on a clock search suggestion, the application viewport is black apart from system overlays. There is no result or error.',
 'C016':'The first launcher search suggestion was tapped, but the delivered app viewport is black with no readable destination, controls, or response.',
 'C088':'The Simple Gallery Pro suggestion list is replaced by a black viewport without a search result or error.',
 'C113':'After tapping the AndroidWorld app entry, the candidate is a blank white viewport with system overlays only; no identifiable destination or failure is visible.',
 'J259':'A scroll on the launcher is followed by a black viewport with only system overlays. Neither a changed scroll position nor a boundary is visible.'})
select('normal_unrelated_destination',{
 'C261':'The highlighted tap is on Calendar in the launcher, but the delivered page is Files / Downloads; it does not show what happened to the Calendar tap.',
 'C315':'The Clock label was tapped in the launcher. The candidate is Files / Downloads, with neither Clock nor a response about it.',
 'C355':'The before view already highlights Network & internet, but this tap is on the separate Apps row. The candidate opens Network & internet, not an outcome on Apps.',
 'C441':'The tap is on the Joplin launcher icon. The candidate shows Audio Recorder onboarding with no Joplin view or explicit failure.',
 'C444':'The Joplin dock icon was tapped. The delivered page is Google Lens, with no visible response on Joplin.'})
lookup={r['review_code']:r for r in lines(W/'review-index.jsonl')}
lookup.update({r['match_id']:r for r in lines(W/'matched.jsonl')})
known={o['pair_id']:mkclean(o)|{'label':o['label']} for o in lines(V1/'additional-archive-observations.jsonl') if o['suite']=='archive_android' and o['label']}
seen=list(known.values()); keep=[]; skipped=[]
for code,(kind,reason) in d.items():
    r=lookup[code];a=r['action']
    def similar(o):
        if distance(a,o['action'])>60:return False
        fr,md=diff(r['before'],o['before'])
        if fr>.012 or md>1.7:return False
        fr,md=diff(r['candidate'],o['candidate'])
        return fr<=.012 and md<=1.7
    conflict=next((z for z in seen if similar(z)),None)
    if conflict:
        skipped.append((code,conflict.get('label','selected'),conflict.get('v1_pair_id',conflict.get('pair_id'))));continue
    seen.append(r);c=r.get('control')
    row=dict(pair_id=r['pair_id'],source_run=r['run'],step=r['step'],review_code=code,kind=kind,reason=reason,
             control=None if not c else dict(pair_id=apair(c['before'],c['action'],c['candidate']),source_run=c['run'],step=c['step'],later_repeat=r['control_evidence']['later_repeat_in_same_trajectory']))
    keep.append(row)
out(HERE/'build/review-decisions.jsonl',keep);print('accepted',len(keep),Counter(r['kind'] for r in keep),'near duplicates omitted',skipped,flush=True)
