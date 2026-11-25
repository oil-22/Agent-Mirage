"""Download pinned public artifacts; never import repository code. Verify HF identities."""
import argparse, concurrent.futures, hashlib, json, os, pathlib, time, urllib.request

MODELS = {
    'jev_style': ('chaoliangUNSW/Jev-Style-2B-Decision-v4', '9d3147c2ba1d793958e447b0e7e20c7436ec34b5'),
    'neohorse': ('TokenRhythm/NeoHorse-Jev-4B', '434cb21d3a994a953d3ae5788405fcb2c4970554'),
}

def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent':'Mirage-local-deployment/1'}), timeout=90) as r:
        return r.read()

def digest(path, mode='sha256'):
    h=hashlib.new(mode)
    if mode=='sha1': h.update(('blob %d\0'%path.stat().st_size).encode())
    with path.open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''): h.update(block)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',required=True);ap.add_argument('--small-only',action='store_true');ap.add_argument('--endpoint',default='https://huggingface.co');ap.add_argument('--identity-root');ap.add_argument('--model',choices=list(MODELS));a=ap.parse_args()
    root=pathlib.Path(a.root);root.mkdir(parents=True,exist_ok=True)
    for key,(repo,rev) in MODELS.items():
        if a.model and key!=a.model:continue
        dest=root/key;dest.mkdir(exist_ok=True)
        raw=(pathlib.Path(a.identity_root)/(key+'.json')).read_bytes() if a.identity_root else fetch(a.endpoint+'/api/models/'+repo+'/revision/'+rev+'?blobs=true')
        meta=json.loads(raw);assert meta['sha']==rev
        (dest/'HF-identity.json').write_bytes(raw)
        items=[s for s in meta['siblings'] if not s['rfilename'].startswith('assets/') and (not a.small_only or s.get('size',0)<20_000_000)]
        def one(s):
            name=s['rfilename'];p=dest/name
            assert not pathlib.PurePosixPath(name).is_absolute() and '..' not in pathlib.PurePosixPath(name).parts
            p.parent.mkdir(parents=True,exist_ok=True)
            expected=(s.get('lfs') or {}).get('sha256');oid=s.get('blobId');size=s.get('size')
            def valid(q):
                return q.exists() and (size is None or q.stat().st_size==size) and (digest(q)==expected if expected else digest(q,'sha1')==oid)
            reused=valid(p)
            if not reused:
                part=p.with_name(p.name+'.partial')
                for attempt in range(4):
                    try:
                        offset=part.stat().st_size if part.exists() else 0
                        headers={'User-Agent':'Mirage-local-deployment/1'}
                        if offset: headers['Range']='bytes=%d-'%offset
                        url=a.endpoint+'/'+repo+'/resolve/'+rev+'/'+name
                        with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=120) as r:
                            append=offset and r.status==206
                            with part.open('ab' if append else 'wb') as f:
                                for block in iter(lambda:r.read(8*1024*1024),b''):f.write(block)
                        if not valid(part): raise ValueError('size or publisher identity mismatch: '+name)
                        os.replace(part,p);break
                    except Exception as e:
                        print(json.dumps({'model':key,'file':name,'attempt':attempt,'error':str(e)}),flush=True)
                        if attempt==3:raise
                        time.sleep(2)
            record={'file':name,'bytes':p.stat().st_size,'sha256':digest(p),'publisher_lfs_sha256':expected,'publisher_git_blob':oid,'reused':reused}
            print(json.dumps({'model':key,**record}),flush=True);return record
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex: records=list(ex.map(one,items))
        receipt={'repo':repo,'revision':rev,'time':time.time(),'small_only':a.small_only,'files':records}
        target=dest/('download-small-receipt.json' if a.small_only else 'download-complete-receipt.json')
        target.write_text(json.dumps(receipt,indent=2),encoding='utf-8')

if __name__=='__main__':main()
