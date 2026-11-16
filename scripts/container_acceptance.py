"""Disposable PDF deployment and backup recovery acceptance."""
import json,secrets,subprocess,tempfile,time,urllib.request,urllib.error
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
name='deck-test-'+secrets.token_hex(5);volume=name+'-data';restored=name+'-restore';key=secrets.token_urlsafe(32);image='deck-post-acceptance:local'
def docker(*args):return subprocess.check_output(['docker',*args],text=True).strip()
def call(base,path,token=key,data=None,method=None):
 raw=json.dumps(data).encode() if data is not None else None
 headers={'Authorization':'Bearer '+token}
 if raw:headers['Content-Type']='application/json'
 with urllib.request.urlopen(urllib.request.Request(base+path,data=raw,headers=headers,method=method),timeout=10) as r:return json.load(r)
def denied(base,path,token):
 try:call(base,path,token);raise AssertionError('Revoked access worked')
 except urllib.error.HTTPError as e:assert e.code==401

def ready(container):
 base='http://127.0.0.1:'+docker('port',container,'8099/tcp').rsplit(':',1)[1]
 for _ in range(100):
  try:
   with urllib.request.urlopen(base,timeout=1) as r:
    if r.status==200:return base
  except (OSError,urllib.error.URLError):time.sleep(.1)
 raise RuntimeError('Service failed to start')
def start(container,vol):
 docker('run','-d','--name',container,'--read-only','--tmpfs','/tmp:size=32m','--cap-drop=ALL','--security-opt=no-new-privileges:true','-e','DECK_OWNER_KEY='+key,'-v',vol+':/data','-p','127.0.0.1::8099',image)
 return ready(container)
try:
 base=start(name,volume);assert docker('exec',name,'id','-u')=='10001'
 import io
 from pypdf import PdfWriter
 w=PdfWriter();w.add_blank_page(width=300,height=200);stream=io.BytesIO();w.write(stream);pdf=stream.getvalue()
 boundary='decktestboundary'
 payload=b'--'+boundary.encode()+b'\r\nContent-Disposition: form-data; name="file"; filename="deck.pdf"\r\nContent-Type: application/pdf\r\n\r\n'+pdf+b'\r\n--'+boundary.encode()+b'--\r\n'
 req=urllib.request.Request(base+'/api/files',data=payload,headers={'Authorization':'Bearer '+key,'Content-Type':'multipart/form-data; boundary='+boundary})
 with urllib.request.urlopen(req) as r:fid=json.load(r)['id']
 url='/api/files/'+fid+'/links'
 active=call(base,url,data={'expires':int(time.time())+3600});revoked=call(base,url,data={'expires':int(time.time())+3600});expired=call(base,url,data={'expires':int(time.time())+2})
 call(base,url+'/'+revoked['id']+'/revoke',data={})
 def download(base):
  with urllib.request.urlopen(urllib.request.Request(base+'/api/links/'+active['id']+'/download',headers={'Authorization':'Bearer '+active['token']})) as r:assert r.read()==pdf
 def check(base,count):
  assert call(base,'/api/files')[0]['id']==fid
  rows=call(base,url);assert next(r for r in rows if r['id']==active['id'])['retrievals']==count
  denied(base,'/api/links/'+revoked['id']+'/download',revoked['token'])
  denied(base,'/api/links/'+expired['id']+'/download',expired['token'])
 download(base);time.sleep(2.1)
 docker('restart','-t','1',name);base=ready(name);check(base,1);download(base);check(base,2)
 docker('stop','-t','1',name)
 with tempfile.TemporaryDirectory() as tmp:
  source=Path(tmp)/'source.sqlite3';backup=Path(tmp)/'backup.sqlite3';docker('cp',name+':/data/deck.sqlite3',str(source))
  subprocess.run(['python3',str(ROOT/'scripts/backup.py'),str(source),str(backup)],check=True);assert backup.stat().st_mode & 0o777==0o600
  assert subprocess.run(['python3',str(ROOT/'scripts/backup.py'),str(source),str(backup)],capture_output=True).returncode!=0
  docker('volume','create',restored)
  docker('run','--rm','--user','0','-v',restored+':/data','-v',str(backup)+':/backup:ro',image,'python','-c',"import shutil,os;shutil.copyfile('/backup','/data/deck.sqlite3');os.chown('/data/deck.sqlite3',10001,10001);os.chmod('/data/deck.sqlite3',0o600);os.chown('/data',10001,10001)")
  base=start(name+'-restored',restored);check(base,2);download(base);check(base,3)
  fresh=call(base,url,data={'expires':int(time.time())+3600});assert call(base,'/api/links/'+fresh['id'],fresh['token'])['filename']=='deck.pdf'
  call(base,url+'/'+active['id']+'/revoke',data={});denied(base,'/api/links/'+active['id']+'/download',active['token'])
 print('PASS: non-root/read-only service; exact PDF bytes, counts, revocation and expiry survive restart/clean-volume restore; new links/revocation work')

finally:
 for container in (name,name+'-restored'):subprocess.run(['docker','rm','-f',container],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 for vol in (volume,restored):subprocess.run(['docker','volume','rm',vol],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
