from collections import deque
class TrendWindows:
    def __init__(self,trend_ids,capacity=3600):self.capacity=capacity;self.data={i:deque(maxlen=capacity) for i in trend_ids}
    def add(self,object_id,value,timestamp):
        if object_id in self.data:self.data[object_id].append({'value':value,'timestamp':timestamp})
    def get(self,object_id):return list(self.data.get(object_id,()))
