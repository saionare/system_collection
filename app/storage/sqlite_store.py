import json, sqlite3, threading, time
from pathlib import Path
class SQLiteStore:
    def __init__(self,path:Path, objects:list[dict]):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True); self.lock=threading.RLock()
        with self.connect() as c:
            c.execute('PRAGMA journal_mode=WAL'); c.execute('PRAGMA synchronous=FULL'); c.execute('PRAGMA busy_timeout=5000')
            c.executescript('''
            CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY AUTOINCREMENT, object_id INTEGER NOT NULL, source_id INTEGER NOT NULL, value_json TEXT NOT NULL, timestamp REAL NOT NULL, changed INTEGER NOT NULL DEFAULT 0);
            CREATE INDEX IF NOT EXISTS idx_history_timestamp_id ON history(timestamp,id);
            CREATE INDEX IF NOT EXISTS idx_history_object_timestamp ON history(object_id,timestamp DESC);
            CREATE TABLE IF NOT EXISTS objects(object_id INTEGER PRIMARY KEY, source_id INTEGER NOT NULL, config_json TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS trend_values(id INTEGER PRIMARY KEY AUTOINCREMENT, object_id INTEGER NOT NULL, value_json TEXT NOT NULL, timestamp REAL NOT NULL);
            CREATE INDEX IF NOT EXISTS idx_trend_object_timestamp ON trend_values(object_id,timestamp DESC,id DESC);
            CREATE TABLE IF NOT EXISTS applied_operations(operation_id TEXT PRIMARY KEY, applied_at REAL NOT NULL);
            ''')
            c.executemany('INSERT OR REPLACE INTO objects(object_id,source_id,config_json) VALUES(?,?,?)',[(o['object_id'],o['source_id'],json.dumps(o)) for o in objects])
    def connect(self):
        c=sqlite3.connect(self.path,timeout=5); c.row_factory=sqlite3.Row; c.execute('PRAGMA busy_timeout=5000'); return c
    def insert_batch(self,rows,operation_id):
        with self.lock, self.connect() as c:
            if c.execute('SELECT 1 FROM applied_operations WHERE operation_id=?',(operation_id,)).fetchone(): return False
            c.executemany('INSERT INTO history(object_id,source_id,value_json,timestamp,changed) VALUES(?,?,?,?,?)',[(r['object_id'],r['source_id'],json.dumps(r['value']),r['timestamp'],int(r.get('changed',False))) for r in rows])
            trends=[r for r in rows if r['object_id']<=20]
            c.executemany('INSERT INTO trend_values(object_id,value_json,timestamp) VALUES(?,?,?)',[(r['object_id'],json.dumps(r['value']),r['timestamp']) for r in trends])
            for oid in range(1,21):
                c.execute('DELETE FROM trend_values WHERE object_id=? AND id NOT IN (SELECT id FROM trend_values WHERE object_id=? ORDER BY timestamp DESC,id DESC LIMIT 3600)',(oid,oid))
            c.execute('INSERT INTO applied_operations VALUES(?,?)',(operation_id,time.time())); return True
    def forget_operation(self,op):
        with self.connect() as c:c.execute('DELETE FROM applied_operations WHERE operation_id=?',(op,))
    def fetch_before(self,cutoff,limit=25000):
        with self.connect() as c: rows=c.execute('SELECT * FROM history WHERE timestamp < ? ORDER BY timestamp,id LIMIT ?',(cutoff,limit)).fetchall()
        return [dict(r) for r in rows]
    def delete_ids(self,ids):
        if not ids:return 0
        deleted=0
        with self.lock,self.connect() as c:
            for i in range(0,len(ids),500):
                part=ids[i:i+500]; cur=c.execute('DELETE FROM history WHERE id IN ('+','.join('?' for _ in part)+')',part);deleted+=cur.rowcount
        return deleted
    def count_history(self):
        with self.connect() as c:return c.execute('SELECT COUNT(*) FROM history').fetchone()[0]
    def count_older_than(self,cutoff):
        with self.connect() as c:return c.execute('SELECT COUNT(*) FROM history WHERE timestamp < ?',(cutoff,)).fetchone()[0]
    def latest_trend(self,object_id,limit=3600):
        with self.connect() as c: rows=c.execute('SELECT value_json,timestamp FROM trend_values WHERE object_id=? ORDER BY timestamp DESC,id DESC LIMIT ?',(object_id,limit)).fetchall()
        return [{'value':json.loads(r['value_json']),'timestamp':r['timestamp']} for r in reversed(rows)]
