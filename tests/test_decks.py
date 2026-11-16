import io,tempfile,unittest,subprocess
from unittest.mock import patch
from pypdf import PdfWriter
from decks import Decks,Invalid,pdf

def fixture(encrypted=False):
 w=PdfWriter();w.add_blank_page(width=100,height=100)
 if encrypted:w.encrypt('secret')
 b=io.BytesIO();w.write(b);return b.getvalue()
class DeckTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.now=1000;self.db=Decks(self.tmp.name+'/db',lambda:self.now);self.data=fixture();self.file=self.db.upload('deck.pdf',self.data);self.link=self.db.create_link(self.file,1100)
 def tearDown(self):self.db.close();self.tmp.cleanup()
 def get(self):return self.db.retrieve(self.link['id'],self.link['token'])
 def test_exact_bytes_and_metadata_not_counted(self):
  self.db.metadata(self.link['id'],self.link['token']);self.assertEqual(self.db.report(self.file)[0]['retrievals'],0);self.assertEqual(self.get()['data'],self.data);self.assertEqual(self.db.report(self.file)[0]['retrievals'],1)
 def test_expiry_boundary(self):
  self.now=1099;self.get();self.now=1100
  with self.assertRaises(Invalid):self.get()
  self.assertEqual(self.db.report(self.file)[0]['retrievals'],1)
 def test_revoked_metadata_and_bytes_denied(self):
  self.db.revoke(self.file,self.link['id'])
  with self.assertRaises(Invalid):self.get()
  with self.assertRaises(Invalid):self.db.metadata(self.link['id'],self.link['token'])
 def test_tokens_are_scoped_and_hashed(self):
  other=self.db.create_link(self.file,1200)
  with self.assertRaises(Invalid):self.db.retrieve(other['id'],self.link['token'])
  self.assertNotIn(self.link['token'],str([dict(r) for r in self.db.db.execute('SELECT * FROM links')]))
 def test_revoke_wrong_file_fails(self):
  other=self.db.upload('other.pdf',self.data)
  with self.assertRaises(Invalid):self.db.revoke(other,self.link['id'])
  self.get()
 def test_invalid_expiries(self):
  for expiry in [1000,999,True,'1200',float('inf'),1000+367*86400]:
   with self.assertRaises(Invalid):self.db.create_link(self.file,expiry)
 def test_quota_rollback(self):
  with patch('decks.MAX_STORAGE',1):
   with self.assertRaises(Invalid):self.db.upload('second.pdf',self.data)
  self.assertEqual(self.db.db.execute('SELECT count(*) FROM files').fetchone()[0],1)
 def test_persistence(self):
  self.get();self.db.close();self.db=Decks(self.tmp.name+'/db',lambda:self.now);self.assertEqual(self.get()['data'],self.data);self.assertEqual(self.db.report(self.file)[0]['retrievals'],2)
class PDFTests(unittest.TestCase):
 def test_invalid_encrypted_and_names(self):
  for name,data in [('deck.pdf',b'bad'),('deck.pdf',fixture(True)),('../deck.pdf',fixture()),('deck\r.pdf',fixture())]:
   with self.assertRaises(Invalid):pdf(name,data)
 def test_worker_timeout(self):
  with patch('decks.subprocess.run',side_effect=subprocess.TimeoutExpired('pdf',5)):
   with self.assertRaises(Invalid):pdf('deck.pdf',fixture())
