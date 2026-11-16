"""Resource-bounded PDF structure check. This is not a content sanitizer."""
import sys
try:
    import resource
    resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024))
    resource.setrlimit(resource.RLIMIT_CPU,(3,3))
    import io,json
    from pypdf import PdfReader
    raw=sys.stdin.buffer.read(10*1024*1024+1)
    if not 1<=len(raw)<=10*1024*1024:raise ValueError('size')
    reader=PdfReader(io.BytesIO(raw),strict=True)
    if reader.is_encrypted:raise ValueError('encrypted')
    pages=len(reader.pages)
    if not 1<=pages<=100:raise ValueError('pages')
    print(json.dumps({'pages':pages}))
except Exception:
    sys.exit(1)
