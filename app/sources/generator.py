import random, time
class SyntheticGenerator:
    def __init__(self, objects: list[dict], seed: int | None=None):
        self.objects=objects; self.rng=random.Random(seed); self.current={o['object_id']:self._value(o) for o in objects}
    def _value(self,o):
        t=o['type']; req=o.get('requirements',{})
        if t=='boolean': return bool(self.rng.getrandbits(1))
        lo=req.get('min',0); hi=req.get('max',1000)
        if t=='integer': return self.rng.randint(int(lo),int(min(hi,10000)))
        return round(self.rng.uniform(float(lo),float(min(hi,10000))),3)
    def snapshot(self):
        now=time.time(); changed=[]
        by_source={s:[o for o in self.objects if o['source_id']==s] for s in range(1,5)}
        for source, objs in by_source.items():
            amount=self.rng.randint(100,600)
            for obj in self.rng.sample(objs,min(amount,len(objs))):
                self.current[obj['object_id']]=self._value(obj)
                changed.append(obj['object_id'])
        rows=[]
        for o in self.objects:
            value=self.current[o['object_id']]
            # Inject occasional bad incoming values to exercise validation; never update persistent current state with them.
            if self.rng.random()<0.003:
                value="invalid" if o['type']!='boolean' else 1
            rows.append({'object_id':o['object_id'],'source_id':o['source_id'],'value':value,'timestamp':now,'changed':o['object_id'] in changed})
        return rows, sorted(changed), now
