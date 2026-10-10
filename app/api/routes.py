from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import Any
from app.processing.validator import Validator
router=APIRouter()
def get_system(request: Request): return request.app.state.system
class ValidationItem(BaseModel):
    object_id:int
    value:Any
class ValidationRequest(BaseModel):
    items:list[ValidationItem]=Field(min_length=1,max_length=4000)
@router.get('/health')
def health(system=Depends(get_system)):return {'status':'ok','running':system.running}
@router.get('/configuration')
def configuration(system=Depends(get_system)):return {'count':len(system.objects),'objects':system.objects}
@router.get('/requirements')
def requirements(system=Depends(get_system)):return {'objects':[{'object_id':o['object_id'],'type':o['type'],'requirements':o['requirements']} for o in system.objects]}
@router.get('/changes')
def changes(source_id:int|None=None, system=Depends(get_system)):
    sources=[]
    for sid in range(1,5):
        if source_id is not None and sid!=source_id:continue
        ids=sorted(i for i in system.last_changed_ids if system.objects_by_id[i]['source_id']==sid)
        ranges=[]
        for oid in ids:
            if not ranges or oid>ranges[-1][1]+1:ranges.append([oid,oid])
            else:ranges[-1][1]=oid
        sources.append({'source_id':sid,'changed_count':len(ids),'changed_ids':ids,'contiguous_ranges':ranges,'min_object_id':ids[0] if ids else None,'max_object_id':ids[-1] if ids else None})
    return {'timestamp':system.last_snapshot_timestamp,'sources':sources}
@router.post('/validate')
def validate(payload:ValidationRequest, system=Depends(get_system)):
    results=[]
    for item in payload.items:
        obj=system.objects_by_id.get(item.object_id)
        if not obj:results.append({'object_id':item.object_id,'valid':False,'reason':'unknown object id'});continue
        ok,reason=Validator.validate(item.value,obj);results.append({'object_id':item.object_id,'valid':ok,'reason':reason})
    return {'results':results,'valid_count':sum(x['valid'] for x in results),'invalid_count':sum(not x['valid'] for x in results)}
@router.get('/trends/{object_id}')
def trend(object_id:int, system=Depends(get_system)):
    if object_id not in system.trend_ids:raise HTTPException(404,'object is not a configured trend')
    return {'object_id':object_id,'capacity':3600,'count':len(system.trends.get(object_id)),'values':system.trends.get(object_id)}
@router.get('/stats')
def stats(system=Depends(get_system)):
    result=dict(system.stats);result.update({'history_rows':system.store.count_history(),'objects':len(system.objects),'sources':4,'trend_objects':len(system.trend_ids),'trend_window_capacity':3600,'last_snapshot_timestamp':system.last_snapshot_timestamp,'older_than_retention':system.store.count_older_than(__import__('time').time()-system.retention_seconds)});return result
