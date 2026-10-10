import json, time
from pathlib import Path
from fastapi.testclient import TestClient
from app.core import CollectionSystem
from main import create_app
ROOT=Path(__file__).resolve().parents[1]
def make_system(tmp_path):
    # Copy only the checked-in config; databases/logs are isolated per test.
    import shutil
    shutil.copytree(ROOT/'config',tmp_path/'config')
    return CollectionSystem(tmp_path,retention_seconds=1)
def test_config_counts(tmp_path):
    s=make_system(tmp_path);assert len(s.objects)==4000;assert len(s.trend_ids)==20;assert {o['source_id'] for o in s.objects}=={1,2,3,4}
def test_validator_rules(tmp_path):
    s=make_system(tmp_path)
    assert s.objects_by_id[1]['requirements']['min']==500
    from app.processing.validator import Validator
    assert Validator.validate(500,s.objects_by_id[1])[0]
    assert not Validator.validate(499,s.objects_by_id[1])[0]
    assert not Validator.validate('500',s.objects_by_id[1])[0]
def test_snapshot_writes_valid_records(tmp_path):
    s=make_system(tmp_path);result=s.process_snapshot()
    assert result['received']==4000;assert result['valid']+result['invalid']==4000;assert s.store.count_history()==result['valid'];assert result['changed_ids']
def test_trend_window_limit(tmp_path):
    s=make_system(tmp_path)
    for i in range(3700):s.trends.add(1,i,time.time())
    values=s.trends.get(1);assert len(values)==3600 and values[0]['value']==100
def test_api_endpoints(tmp_path):
    s=make_system(tmp_path);client=TestClient(create_app(s))
    assert client.get('/configuration').json()['count']==4000
    assert client.get('/requirements').status_code==200
    assert client.get('/changes').status_code==200
    assert client.get('/stats').json()['trend_objects']==20
    assert client.get('/trends/1').status_code==200
    assert client.get('/trends/999').status_code==404
def test_api_validation(tmp_path):
    s=make_system(tmp_path);client=TestClient(create_app(s))
    response=client.post('/validate',json={'items':[{'object_id':1,'value':500},{'object_id':1,'value':2},{'object_id':9999,'value':1}]})
    assert response.status_code==200;data=response.json();assert data['valid_count']==1 and data['invalid_count']==2
def test_archive_removes_expired_rows(tmp_path):
    s=make_system(tmp_path);s.process_snapshot()
    with s.store.connect() as c:c.execute('UPDATE history SET timestamp=?',(time.time()-10,))
    result=s.archive_old();assert result['selected']>0;assert s.store.count_older_than(time.time()-s.retention_seconds)==0
    assert list((tmp_path/'archive').glob('archive_*.jsonl'))
def test_wal_compaction_and_pending(tmp_path):
    from app.storage.wal import CustomWAL
    wal=CustomWAL(tmp_path/'wal.jsonl',compact_every=2)
    op=wal.begin([{'object_id':1,'value':True}]);assert len(wal.pending_operations())==1
    wal.commit(op);assert wal.pending_operations()==[]
    for _ in range(3):wal.begin([])
    wal.compact();assert len(wal.pending_operations())==3
