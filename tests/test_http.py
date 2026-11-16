import io,tempfile,unittest
from server import create_app
from test_decks import fixture
class HTTPTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.now=1000;self.owner={'Authorization':'Bearer '+'x'*48};self.client=create_app(self.tmp.name+'/db','x'*48,lambda:self.now).test_client();self.raw=fixture()
  r=self.client.post('/api/files',headers=self.owner,data={'file':(io.BytesIO(self.raw),'deck.pdf')});self.assertEqual(r.status_code,201);self.file=r.json['id'];self.url='/api/files/'+self.file
  r=self.client.post(self.url+'/links',headers=self.owner,json={'expires':1100});self.assertEqual(r.status_code,201);self.link=r.json;self.path='/api/links/'+self.link['id'];self.reader={'Authorization':'Bearer '+self.link['token']}
 def tearDown(self):self.tmp.cleanup()
 def count(self):return self.client.get(self.url+'/links',headers=self.owner).json[0]['retrievals']
 def test_exact_attachment_and_count_semantics(self):
  self.assertEqual(self.client.get(self.path,headers=self.reader).status_code,200);self.assertEqual(self.client.head(self.path+'/download',headers=self.reader).status_code,200);self.assertEqual(self.count(),0)
  r=self.client.get(self.path+'/download',headers=self.reader);self.assertEqual(r.data,self.raw);self.assertIn('attachment',r.headers['Content-Disposition']);self.assertEqual(r.mimetype,'application/pdf');self.assertEqual(self.count(),1)
 def test_expiry_denies_metadata_head_and_bytes(self):
  self.now=1100
  for method,path in [('get',self.path),('head',self.path+'/download'),('get',self.path+'/download')]:self.assertEqual(getattr(self.client,method)(path,headers=self.reader).status_code,401)
  self.assertEqual(self.count(),0)
 def test_revocation_and_owner_access_separation(self):
  for h in [{},self.reader]:
   for method,path in [('get','/api/files'),('post','/api/files'),('get',self.url+'/links'),('post',self.url+'/links'),('post',self.url+'/links/'+self.link['id']+'/revoke')]:self.assertEqual(getattr(self.client,method)(path,headers=h).status_code,401)
  self.assertEqual(self.client.post(self.url+'/links/'+self.link['id']+'/revoke',headers=self.owner).status_code,200);self.assertEqual(self.client.get(self.path+'/download',headers=self.reader).status_code,401)
 def test_wrong_link_and_query_credentials_denied(self):
  other=self.client.post(self.url+'/links',headers=self.owner,json={'expires':1200}).json
  self.assertEqual(self.client.get('/api/links/'+other['id'],headers=self.reader).status_code,401);self.assertEqual(self.client.get(self.path+'?token='+self.link['token']).status_code,401)
 def test_invalid_expiry_and_upload(self):
  for expiry in [True,1000,'1200',None]:self.assertEqual(self.client.post(self.url+'/links',headers=self.owner,json={'expires':expiry}).status_code,400)
  self.assertEqual(self.client.post('/api/files',headers=self.owner,data={'file':(io.BytesIO(b'bad'),'deck.pdf')}).status_code,400)
 def test_limits_and_security(self):
  r=self.client.post('/api/files',headers=self.owner,data=b'x'*(MAX_REQUEST:=11*1024*1024),content_type='application/octet-stream');self.assertEqual(r.status_code,413)
  self.assertEqual(r.headers['Cache-Control'],'no-store');self.assertEqual(r.headers['X-Content-Type-Options'],'nosniff');self.assertIsNone(r.headers.get('Access-Control-Allow-Origin'))
 def test_range_is_full_attachment_not_misleading_partial_count(self):
  r=self.client.get(self.path+'/download',headers={**self.reader,'Range':'bytes=0-9'});self.assertEqual(r.status_code,200);self.assertEqual(r.data,self.raw);self.assertEqual(self.count(),1)
 def test_report_has_no_secret(self):
  r=self.client.get(self.url+'/links',headers=self.owner);self.assertNotIn(self.link['token'],r.text);self.assertNotIn('token_hash',r.text)
