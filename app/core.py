import json, logging, os, threading, time, uuid
from pathlib import Path
from app.archive.service import ArchiveService
from app.processing.validator import Validator
from app.sources.generator import SyntheticGenerator
from app.storage.sqlite_store import SQLiteStore
from app.storage.wal import CustomWAL
from app.trends.windows import TrendWindows
log=logging.getLogger(__name__)
class CollectionSystem:
    def __init__(self,root:Path,retention_seconds=None,archive_interval_seconds=1.0):
        self.root=Path(root);self.objects=json.loads((self.root/'config/objects.json').read_text(encoding='utf-8'));self.objects_by_id={o['object_id']:o for o in self.objects}
        self.trend_ids={o['object_id'] for o in self.objects if o.get('trend')};assert len(self.objects)==4000 and len({o['source_id'] for o in self.objects})==4 and len(self.trend_ids)==20
        self.retention_seconds=float(retention_seconds if retention_seconds is not None else os.getenv('ARCHIVE_RETENTION_SECONDS','60'))
        self.archive_interval_seconds=archive_interval_seconds;self.store=SQLiteStore(self.root/'database/history.sqlite3',self.objects);self.wal=CustomWAL(self.root/'logs/custom_wal.jsonl')
        self.archive=ArchiveService(self.store,self.root/'archive',self.objects_by_id,self.root/'logs/archive_wal.jsonl');self.generator=SyntheticGenerator(self.objects);self.trends=TrendWindows(self.trend_ids,3600)
        self.running=False;self.last_changed_ids=[];self.last_snapshot_timestamp=None;self.lock=threading.RLock()
        self.stats={'received':0,'valid':0,'invalid':0,'written':0,'archived':0,'archive_deleted':0,'errors':0,'last_snapshot_ms':0.0,'last_archive_timestamp':None,'last_archive_error':None,'retention_seconds':self.retention_seconds}
        self._restore_trends();self._recover_wal()
    def _restore_trends(self):
        for oid in self.trend_ids:
            for row in self.store.latest_trend(oid,3600):self.trends.add(oid,row['value'],row['timestamp'])
    def _recover_wal(self):
        for op in self.wal.pending_operations():
            try:self.store.insert_batch(op['rows'],op['operation_id']);self.wal.commit(op['operation_id']);self.store.forget_operation(op['operation_id'])
            except Exception:log.exception('WAL recovery failed for %s',op.get('operation_id'))
    def process_snapshot(self):
        start=time.perf_counter();rows,changed,stamp=self.generator.snapshot();valid_rows=[];invalid=0
        for row in rows:
            obj=self.objects_by_id[row['object_id']];ok,reason=Validator.validate(row['value'],obj)
            if ok:
                valid_rows.append(row)
                if row['object_id'] in self.trend_ids:self.trends.add(row['object_id'],row['value'],row['timestamp'])
            else:
                invalid+=1;log.warning('Rejected value object_id=%s value=%r reason=%s',row['object_id'],row['value'],reason)
        op=self.wal.begin(valid_rows)
        try:
            self.store.insert_batch(valid_rows,op);self.wal.commit(op);self.store.forget_operation(op)
        except Exception:
            self.stats['errors']+=1;log.exception('Snapshot persistence failed; operation retained in custom WAL');raise
        with self.lock:self.last_changed_ids=changed;self.last_snapshot_timestamp=stamp
        self.stats['received']+=len(rows);self.stats['valid']+=len(valid_rows);self.stats['invalid']+=invalid;self.stats['written']+=len(valid_rows);self.stats['last_snapshot_ms']=round((time.perf_counter()-start)*1000,3)
        return {'timestamp':stamp,'received':len(rows),'valid':len(valid_rows),'invalid':invalid,'changed_ids':changed,'duration_ms':self.stats['last_snapshot_ms']}
    def archive_old(self):
        try:
            result=self.archive.run_once(time.time()-self.retention_seconds)
            self.stats['archived']+=result['archived'];self.stats['archive_deleted']+=result['deleted'];self.stats['last_archive_timestamp']=time.time();self.stats['last_archive_error']=None
            if result['selected']:log.info('Archive batch committed: selected=%s archived=%s rejected=%s deleted=%s',result['selected'],result['archived'],result['rejected'],result['deleted'])
            return result
        except Exception as e:self.stats['errors']+=1;self.stats['last_archive_error']=str(e);log.exception('Archive batch failed');return {'error':str(e)}
    def _archive_loop(self):
        while self.running:
            self.archive_old();time.sleep(self.archive_interval_seconds)
    def run_forever(self):
        self.running=True;threading.Thread(target=self._archive_loop,daemon=True,name='archive-worker').start();next_tick=time.monotonic()
        while self.running:
            try:self.process_snapshot()
            except Exception:log.exception('Snapshot failed')
            next_tick+=1;delay=next_tick-time.monotonic()
            if delay>0:time.sleep(delay)
            else:next_tick=time.monotonic()
    def stop(self):self.running=False
