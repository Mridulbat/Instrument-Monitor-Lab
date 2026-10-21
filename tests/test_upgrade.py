import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from engine import analyze
from live import LiveMonitor

def samples(values):
    return [dict(time_s=i,raw_mA=None if v is None else 4.1+.158*v) for i,v in enumerate(values)]

class QualityTests(unittest.TestCase):
    def test_high_held_during_missing(self):
        r=analyze(samples([90,90,None,None]))['rows']
        self.assertIn('HIGH',r[-1]['flags']);self.assertEqual(r[-1]['quality'],'BAD')
    def test_recovery_requires_two_good(self):
        r=analyze(samples([90,90,None,50,50]))['rows']
        self.assertIn('HIGH',r[-2]['flags']);self.assertEqual(r[-2]['quality'],'RECOVERING');self.assertNotIn('HIGH',r[-1]['flags'])
    def test_repeated_dropout_resets_recovery(self):
        r=analyze(samples([90,None,50,None,50,50]))['rows']
        self.assertIn('HIGH',r[-2]['flags']);self.assertEqual(r[-1]['quality'],'GOOD')
    def test_stale_holds_alarm(self):
        data=samples([90,90]);data[-1]['age_s']=3
        r=analyze(data)['rows'][-1];self.assertIn('STALE',r['flags']);self.assertIn('HIGH',r['flags'])
    def test_spike_and_reference_drift(self):
        data=samples([50]*6+[75]);self.assertIn('SPIKE',analyze(data)['rows'][-1]['flags'])
        data=samples([55]*6)
        for r in data:r['reference']=50
        self.assertIn('DRIFT',analyze(data)['rows'][-1]['flags'])
    def test_no_reference_no_drift_claim(self):
        self.assertNotIn('DRIFT',analyze(samples([55]*6))['rows'][-1]['flags'])
    def test_live_frozen_heartbeat(self):
        tags=dict(sensor_mA=18.32,device_quality=0,heartbeat=1)
        with patch('live.time.monotonic',side_effect=[0,1,4]),patch('live.read_registers',return_value=tags):
            client=LiveMonitor();client.poll();r=client.poll()
        self.assertIn('STALE',r['active_flags']);self.assertIn('HIGH',r['active_flags'])
    def test_live_disconnect(self):
        with patch('live.read_registers',side_effect=OSError('offline')):
            r=LiveMonitor().poll()
        self.assertEqual(r['quality'],'BAD');self.assertIn('MISSING',r['active_flags'])
