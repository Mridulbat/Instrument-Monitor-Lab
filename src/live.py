"""Bounded live-poll history and wall-clock stale detection."""
import time
from engine import analyze
from modbus_wire import read_registers

class LiveMonitor:
    def __init__(self):
        self.started=time.monotonic();self.changed=self.started;self.heartbeat=None;self.samples=[]
    def poll(self):
        now=time.monotonic();message='Connected';tags=None
        try:
            tags=read_registers()
            if tags['heartbeat']!=self.heartbeat:self.changed=now;self.heartbeat=tags['heartbeat']
            age=now-self.changed
            raw=tags['sensor_mA'] if tags['device_quality']==0 else None
        except (OSError,ValueError,ConnectionError) as error:
            message='Communication unavailable: '+str(error);raw=None;age=max(3,now-self.changed)
        self.samples.append(dict(time_s=now-self.started,raw_mA=raw,age_s=age))
        # Fixed bounded session: keep full alarm history, require reset beyond 10,000 polls.
        if len(self.samples)>10000:
            self.samples.pop();raise ValueError('Live session reached 10,000 polls; restart the monitor server.')
        result=analyze(self.samples)
        result.update(tags=tags,communication=message,age_s=round(age,2),quality=result['rows'][-1]['quality'],active_flags=result['rows'][-1]['flags'])
        return result
