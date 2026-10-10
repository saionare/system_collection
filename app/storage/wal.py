import json, os, threading, uuid
from pathlib import Path
class CustomWAL:
    def __init__(self,path:Path,compact_every=10,max_bytes=8*1024*1024):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True);self.lock=threading.RLock();self.compact_every=compact_every;self.max_bytes=max_bytes;self.commits=0
        self.path.touch(exist_ok=True)
    def _append(self,item):
        data=(json.dumps(item,separators=(',',':'))+'\n').encode()
        with open(self.path,'ab') as f:f.write(data);f.flush();os.fsync(f.fileno())
    def begin(self,rows):
        op=uuid.uuid4().hex
        with self.lock:self._append({'kind':'BEGIN','operation_id':op,'rows':rows})
        return op
    def commit(self,op):
        with self.lock:
            self._append({'kind':'COMMIT','operation_id':op});self.commits+=1
            if self.commits>=self.compact_every or self.path.stat().st_size>=self.max_bytes:self.compact()
    def pending_operations(self):
        with self.lock:
            states={}
            try: lines=self.path.read_text(encoding='utf-8').splitlines()
            except FileNotFoundError:return []
            for line in lines:
                try:r=json.loads(line)
                except Exception:continue
                op=r.get('operation_id')
                if not op:continue
                if r.get('kind')=='BEGIN':states[op]=r
                elif r.get('kind')=='COMMIT':states.pop(op,None)
            return list(states.values())
    def compact(self):
        with self.lock:
            pending=self.pending_operations();tmp=self.path.with_suffix('.tmp')
            with open(tmp,'w',encoding='utf-8') as f:
                for r in pending:f.write(json.dumps(r,separators=(',',':'))+'\n')
                f.flush();os.fsync(f.fileno())
            os.replace(tmp,self.path);self.commits=0
