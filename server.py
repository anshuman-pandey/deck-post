"""Local authenticated PDF sharing API; no public deployment configured."""
import hmac,io,os,sqlite3,time
from flask import Flask,g,request,jsonify,abort,send_file
from werkzeug.exceptions import HTTPException
from decks import Decks,Invalid,MAX_FILE

def create_app(path,owner_key,clock=time.time):
    if not isinstance(owner_key,str) or not owner_key.isascii() or len(owner_key)<32:raise ValueError('Set DECK_OWNER_KEY to at least 32 random ASCII characters.')
    app=Flask(__name__,static_folder=None);app.config.update(MAX_CONTENT_LENGTH=MAX_FILE+65536,MAX_FORM_MEMORY_SIZE=65536,MAX_FORM_PARTS=2)
    def db():
        if 'db' not in g:g.db=Decks(path,clock)
        return g.db
    def token():
        value=request.headers.get('Authorization','');return value[7:] if value.startswith('Bearer ') else ''
    def owner():
        if not hmac.compare_digest(token().encode(),owner_key.encode()):abort(401,description='Owner access denied.')
    def access(key):
        try:return db().metadata(key,token())
        except Invalid:abort(401,description='Link unavailable, expired or revoked.')
    def data():
        body=request.get_json()
        if not isinstance(body,dict):raise Invalid('Expected a JSON object.')
        return body
    @app.teardown_appcontext
    def close(error):
        store=g.pop('db',None)
        if store:store.close()
    @app.after_request
    def headers(r):
        r.headers.update({'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer','Content-Security-Policy':"default-src 'none'; frame-ancestors 'none'; base-uri 'none'"});return r
    @app.errorhandler(Invalid)
    def invalid(e):return jsonify(error=str(e)),400
    @app.errorhandler(HTTPException)
    def http_error(e):return jsonify(error=e.description),e.code
    @app.errorhandler(sqlite3.OperationalError)
    def storage(e):return jsonify(error='Storage unavailable. Please retry.'),503
    @app.get('/api/files')
    def listing():
        owner();return jsonify([dict(r) for r in db().db.execute('SELECT id,filename,sha256,pages,length(data) AS bytes FROM files ORDER BY rowid DESC')])
    @app.post('/api/files')
    def upload():
        owner();file=request.files.get('file')
        if file is None:raise Invalid('Choose a PDF file.')
        return jsonify(id=db().upload(file.filename,file.stream.read(MAX_FILE+1))),201
    @app.post('/api/files/<file>/links')
    def link(file):owner();body=data();return jsonify(db().create_link(file,body.get('expires'))),201
    @app.get('/api/files/<file>/links')
    def report(file):owner();return jsonify(db().report(file))
    @app.post('/api/files/<file>/links/<key>/revoke')
    def revoke(file,key):owner();db().revoke(file,key);return jsonify(ok=True)
    @app.get('/api/links/<key>')
    def metadata(key):return jsonify(access(key))
    @app.get('/api/links/<key>/download')
    def download(key):
        access(key)
        # HEAD validates access but must never record a file retrieval.
        if request.method=='HEAD':return '',200,{'Content-Type':'application/pdf'}
        try:file=db().retrieve(key,token())
        except Invalid:abort(401,description='Link unavailable, expired or revoked.')
        response=send_file(io.BytesIO(file['data']),mimetype='application/pdf',as_attachment=True,download_name=file['filename'],conditional=False,etag=False)
        response.headers['X-Content-SHA256']=file['sha256'];return response
    return app

if __name__=='__main__':
    os.umask(0o077)
    create_app(os.environ.get('DECK_DATABASE','deck.sqlite3'),os.environ.get('DECK_OWNER_KEY','')).run(host='127.0.0.1',port=8099)
