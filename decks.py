"""Immutable PDF files and expiring download credentials; not read analytics."""
import hashlib,hmac,json,secrets,sqlite3,subprocess,sys,time,unicodedata
from pathlib import Path
MAX_FILE=10*1024*1024
MAX_STORAGE=100*1024*1024
class Invalid(ValueError):pass

def pdf(filename,data):
    if not isinstance(filename,str) or not 1<=len(filename)<=200 or '/' in filename or '\\' in filename or any(unicodedata.category(c).startswith('C') for c in filename) or not filename.lower().endswith('.pdf'):raise Invalid('Use a plain PDF filename.')
    if type(data) is not bytes or not 1<=len(data)<=MAX_FILE:raise Invalid('PDF must contain 1 byte to 10 MiB.')
    try:
        result=subprocess.run([sys.executable,'-I',str(Path(__file__).with_name('pdf_check.py'))],input=data,capture_output=True,timeout=5,check=True)
        pages=json.loads(result.stdout)['pages']
        if type(pages) is not int or not 1<=pages<=100:raise ValueError('pages')
    except (subprocess.SubprocessError,OSError,ValueError,KeyError,TypeError) as e:raise Invalid('PDF check failed. Use an unencrypted PDF with 1 to 100 pages within processing limits.') from e
    return pages

def digest(token):return hashlib.sha256(token.encode()).hexdigest()
class Decks:
    """Owner methods require authentication at a future HTTP boundary."""
    def __init__(self,path,clock=time.time):
        self.clock=clock;self.db=sqlite3.connect(path);self.db.row_factory=sqlite3.Row;self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript('''CREATE TABLE IF NOT EXISTS files(id TEXT PRIMARY KEY,filename TEXT,data BLOB,sha256 TEXT,pages INTEGER);
        CREATE TABLE IF NOT EXISTS links(id TEXT PRIMARY KEY,file TEXT REFERENCES files(id),token_hash TEXT,expires INTEGER,revoked INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS retrievals(link TEXT REFERENCES links(id),at INTEGER);''')
    def close(self):self.db.close()
    def upload(self,filename,data):
        pages=pdf(filename,data);key=secrets.token_urlsafe(16)
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            size=self.db.execute('SELECT COALESCE(sum(length(data)),0) FROM files').fetchone()[0]
            if size+len(data)>MAX_STORAGE:raise Invalid('Storage limit reached (100 MiB).')
            self.db.execute('INSERT INTO files VALUES(?,?,?,?,?)',(key,filename,data,hashlib.sha256(data).hexdigest(),pages))
        return key
    def create_link(self,file,expires):
        now=int(self.clock())
        if type(expires) is not int or not now<expires<=now+366*86400:raise Invalid('Expiry must be in the next 366 days as an integer UTC timestamp.')
        key=secrets.token_urlsafe(16);token=secrets.token_urlsafe(32)
        with self.db:
            if not self.db.execute('SELECT 1 FROM files WHERE id=?',(file,)).fetchone():raise Invalid('File not found.')
            self.db.execute('INSERT INTO links VALUES(?,?,?,?,0)',(key,file,digest(token),expires))
        return dict(id=key,token=token,expires=expires)
    def auth(self,key,token):
        row=self.db.execute('SELECT * FROM links WHERE id=?',(key,)).fetchone()
        if row is None or row['revoked'] or self.clock()>=row['expires'] or not isinstance(token,str) or not hmac.compare_digest(row['token_hash'],digest(token)):raise Invalid('Link unavailable, expired or revoked.')
        return row
    def metadata(self,key,token):
        row=self.auth(key,token);file=self.db.execute('SELECT filename,sha256,pages FROM files WHERE id=?',(row['file'],)).fetchone()
        return dict(file,expires=row['expires'])
    def retrieve(self,key,token):
        with self.db:
            self.db.execute('BEGIN IMMEDIATE');link=self.auth(key,token)
            row=self.db.execute('SELECT filename,data,sha256 FROM files WHERE id=?',(link['file'],)).fetchone()
            self.db.execute('INSERT INTO retrievals VALUES(?,?)',(key,int(self.clock())))
        return dict(row)
    def revoke(self,file,key):
        with self.db:
            if not self.db.execute('UPDATE links SET revoked=1 WHERE id=? AND file=?',(key,file)).rowcount:raise Invalid('Link not found.')
    def report(self,file):
        if not self.db.execute('SELECT 1 FROM files WHERE id=?',(file,)).fetchone():raise Invalid('File not found.')
        return [dict(r) for r in self.db.execute('SELECT id,expires,revoked,(SELECT count(*) FROM retrievals WHERE link=links.id) AS retrievals FROM links WHERE file=?',(file,))]
