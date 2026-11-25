"""Fresh read-only source collection, not an agent trajectory or formal experiment."""
import argparse,hashlib,json,time,traceback
from pathlib import Path
from playwright.sync_api import sync_playwright

def main(root):
    assert not(root/'source-summary.json').exists()
    images=root/'images';images.mkdir();rows=[];attempts=[]
    def capture(page,name,http_status=None):
        raw=page.screenshot();h=hashlib.sha256(raw).hexdigest();(images/(h+'.png')).write_bytes(raw)
        row={'id':name,'observation_id':'fresh-source-'+name+'-'+str(time.time_ns()),'image_sha256':h,
             'observed_at':time.time(),'viewport':[1280,720],'url':page.url,'http_status':http_status,
             'scripted_source_attempts':list(attempts),'recent_action':json.dumps(attempts[-1]['native_payload'])if attempts else '',
             'execution_feedback':json.dumps({'source_script_returned':True,'result_state':'requires_actual_current_image_not_execution_alone'})}
        rows.append(row);(root/(name+'-source.json')).write_text(json.dumps(row,indent=2))
    def record(payload):attempts.append({'native_payload':payload,'time':time.time(),'actor':'predeclared source collection script, not model output'})
    with sync_playwright()as pw:
        browser=pw.chromium.launch(headless=True);context=browser.new_context(viewport={'width':1280,'height':720})
        context.tracing.start(screenshots=True,snapshots=False,sources=False);page=context.new_page()
        try:
            response=page.goto('http://192.0.2.10:29980/',wait_until='networkidle',timeout=30000)
            capture(page,'home',response.status)
            page.mouse.click(302*1.28,418*.72);record({'type':'click','x':302,'y':418});page.wait_for_timeout(500);capture(page,'focus')
            page.keyboard.type('basketball');record({'type':'type','text':'basketball'});page.wait_for_timeout(500);capture(page,'typed')
            page.mouse.click(806*1.28,418*.72);record({'type':'click','x':806,'y':418});page.wait_for_load_state('networkidle',timeout=30000);capture(page,'results-top')
            for i in range(1,8):
                page.mouse.wheel(0,650);record({'type':'scroll','direction':'down','source_scroll_pixels':650});page.wait_for_timeout(500);capture(page,'scroll-%02d'%i)
            query='MirageScopedReadinessNegative'+str(time.time_ns())
            response=page.goto('http://192.0.2.10:29980/index.php?page=search&sPattern='+query,wait_until='networkidle',timeout=30000)
            record({'type':'source_get','scope':'read-only no-results control, not native actor action'});capture(page,'no-results',response.status)
            page.goto('about:blank');record({'type':'source_get','scope':'genuine blank surrogate, not website loading evidence'});capture(page,'blank')
            summary={'phase':'completed','rows':rows,'native_actor_calls':0,'verifier_calls':0,'model_controlled_GUI_actions':0,
                     'scripted_source_operations':len(attempts),'site_reset':False,'fixture_import':False,'DOM_AX_collected':False,
                     'scope':'Fresh1280x720 unmodified screenshots with complete scripted collection provenance. Not original task trajectories, semantic labels or a formal efficacy trial. about:blank is a blank negative surrogate, not a positive loading condition.'}
            (root/'source-summary.json').write_text(json.dumps(summary,indent=2))
        finally:
            context.tracing.stop(path=str(root/'browser-trace.zip'));browser.close()

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);a=ap.parse_args()
    try:main(a.root)
    except BaseException:
        (a.root/'failure.json').write_text(json.dumps({'traceback':traceback.format_exc(),'model_calls':0}));raise
