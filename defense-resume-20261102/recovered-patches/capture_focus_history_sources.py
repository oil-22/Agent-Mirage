"""New read-only browser source sequence; not an actor trajectory or semantic labels."""
import argparse,hashlib,json,time
from pathlib import Path
from urllib.parse import quote
from playwright.sync_api import sync_playwright

def main(root):
    images=root/'images';images.mkdir();rows=[];attempts=[]
    def record(payload):attempts.append({'payload':payload,'time':time.time(),'origin':'predeclared source script, not native actor inference'})
    def capture(page,name):
        raw=page.screenshot();h=hashlib.sha256(raw).hexdigest();(images/(h+'.png')).write_bytes(raw)
        rows.append({'id':name,'sha256':h,'observed_at':time.time(),'url':page.url,'viewport':[1280,720],'attempts':list(attempts)})
    with sync_playwright()as pw:
        browser=pw.chromium.launch(headless=True);ctx=browser.new_context(viewport={'width':1280,'height':720});ctx.tracing.start(screenshots=True,snapshots=False,sources=False);page=ctx.new_page()
        try:
            page.goto('http://192.0.2.10:29980/index.php?page=search&sPattern=basketball',wait_until='networkidle');record({'type':'source_get','purpose':'read-only source observation'});capture(page,'prior-results')
            page.mouse.click(230,196);record({'type':'click','pixel_point':[230,196]});page.wait_for_timeout(300);capture(page,'query-cue')
            page.mouse.click(1170,112);record({'type':'click','pixel_point':[1170,112]});page.wait_for_timeout(300);capture(page,'query-ordinary')
            page.goto('http://192.0.2.10:29980/',wait_until='networkidle');record({'type':'source_get','purpose':'read-only source observation'})
            page.mouse.click(386,301);record({'type':'click','pixel_point':[386,301]});page.keyboard.type('basketball');record({'type':'type','text':'basketball'});page.wait_for_timeout(300);capture(page,'home-cue')
            page.mouse.click(1180,370);record({'type':'click','pixel_point':[1180,370]});page.wait_for_timeout(300);capture(page,'home-ordinary')
            query='copper lantern '+str(time.time_ns());page.goto('http://192.0.2.10:29980/index.php?page=search&sPattern='+quote(query),wait_until='networkidle');record({'type':'source_get','purpose':'read-only alternate-query observation'})
            page.mouse.click(228,264);record({'type':'click','pixel_point':[228,264]});page.wait_for_timeout(300);capture(page,'city-cue')
            page.mouse.click(1160,420);record({'type':'click','pixel_point':[1160,420]});page.wait_for_timeout(300);capture(page,'city-ordinary')
            (root/'source-summary.json').write_text(json.dumps({'rows':rows,'phase':'completed','scripted_operations':len(attempts),'model_calls':0,'model_GUI_actions':0,'site_reset':False,'DOM_AX_exported':False,'logged_in':False,'scope':'New source capture, ordinary style/cue appearance must be independently reviewed. Names describe collection intent, not expected semantic labels. Current/previous pixels may repeat site content; not independent tasks.'},indent=2))
        finally:ctx.tracing.stop(path=str(root/'browser-trace.zip'));browser.close()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);main(p.parse_args().root)
