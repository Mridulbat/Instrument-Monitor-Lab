import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from calibration import fit
from study import calibrations, run, score, PARAMETERS
from validation import Validator


class CalibrationTests(unittest.TestCase):
    def test_invalid_data(self):
        for x, y in [([1]*4,[1,2,3,4]), ([0,1],[4,5]), ([0,1,2,3],[4,5,6,float('nan')]), ([0,1,2,3],[4,3,2,1]), ([0,1,2,3],[4,5,6,7])]:
            with self.assertRaises(ValueError): fit(x,y)

    def test_independent_inverse_and_uncertainty(self):
        cals, _ = calibrations()
        for cal, (a,b) in zip(cals, PARAMETERS):
            v, variance = cal.measure(a+b*55)
            self.assertLess(abs(v-55), .2)
            self.assertGreater(variance, 0)
            self.assertGreater(cal.measure(a+b*99)[1], cal.measure(a+b*50)[1])

    def test_invalid_and_extrapolated_measurement(self):
        cal = calibrations()[0][0]
        for value in (None, float('nan'), float('inf'), 0, 22, 20.4):
            with self.assertRaises(ValueError): cal.measure(value)


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.cals, _ = calibrations()
        self.detector = Validator(self.cals)

    def raw(self, values):
        return [c.intercept+c.slope*v if v is not None else None for c,v in zip(self.cals, values)]

    def test_process_step_is_not_sensor_failure(self):
        s = score(run('step', 1001))
        self.assertEqual(s['fp'], 0)
        self.assertEqual(s['available'], s['samples']-1)

    def test_isolation_requires_three_samples_and_recovers(self):
        for t in range(3): r = self.detector.update(t,self.raw([60,50,50]))
        self.assertEqual(r['isolated'], [0]); self.assertAlmostEqual(r['value'],50)
        r = self.detector.update(3,self.raw([50,50,50]))
        self.assertEqual(r['isolated'], [])

    def test_no_agreement_unknown(self):
        r = self.detector.update(0,self.raw([20,50,80]))
        self.assertEqual(r['quality'],'UNKNOWN'); self.assertIsNone(r['value'])

    def test_ambiguous_chain_does_not_select_a_pair(self):
        r=self.detector.update(0,self.raw([50,50.9,51.8]))
        self.assertEqual(r['quality'],'UNKNOWN')

    def test_invalid_shape_and_age(self):
        with self.assertRaises(ValueError): self.detector.update(0,[12,12])
        r=self.detector.update(0,self.raw([50]*3),[float('nan'),0,0])
        self.assertEqual(r['invalid'],[0])

    def test_repeated_dropouts_restart_recovery(self):
        for t in range(6):
            r=self.detector.update(t,[None]*3 if t%2==0 else self.raw([50]*3))
            self.assertIsNone(r['value'])

    def test_dual_fault_can_isolate_the_healthy_channel(self):
        r=run('dual_fault',1001)['rows'][100]
        self.assertEqual(r['isolated'],[2]); self.assertGreater(abs(r['value']-r['truth']),5)

    def test_shared_uncertainty_not_divided_by_three(self):
        self.detector.update(0,self.raw([50]*3))
        r = self.detector.update(1,self.raw([50]*3))
        independent = sum(c.measure(c.intercept+c.slope*50)[1] for c in self.cals)/9
        expected = 2*math.sqrt(independent+.05**2)
        self.assertAlmostEqual(r['expanded_u'],expected)

    def test_active_alarm_held_through_missing_and_recovery(self):
        for t in (0,1): self.detector.update(t,self.raw([85]*3))
        r=self.detector.update(2,[None]*3)
        self.assertTrue(r['high']); self.assertEqual(r['quality'],'UNKNOWN')
        r=self.detector.update(3,self.raw([50]*3))
        self.assertTrue(r['high']); self.assertEqual(r['quality'],'RECOVERING')
        self.assertFalse(self.detector.update(4,self.raw([50]*3))['high'])

    def test_alarm_uncertainty_and_hysteresis(self):
        for t in (0,1): r=self.detector.update(t,self.raw([80]*3))
        self.assertFalse(r['high'])
        self.assertTrue(self.detector.update(2,self.raw([85]*3))['high'])
        self.assertTrue(self.detector.update(3,self.raw([78]*3))['high'])
        self.assertFalse(self.detector.update(4,self.raw([76]*3))['high'])

    def test_stale_and_one_channel_are_unknown(self):
        r=self.detector.update(0,self.raw([50]*3),[0,3,3])
        self.assertEqual(r['invalid'],[1,2]); self.assertIsNone(r['value'])

    def test_timestamps(self):
        self.detector.update(0,self.raw([50]*3))
        for t in (0,-1,float('nan')):
            with self.assertRaises(ValueError): self.detector.update(t,self.raw([50]*3))
        r=self.detector.update(4,self.raw([50]*3))
        self.assertEqual(r['quality'],'UNKNOWN')

    def test_common_mode_is_an_explicit_blind_spot(self):
        s=score(run('common_mode',1001))
        self.assertEqual(s['detected'],0)
        self.assertGreater(s['rmse'],2)

    def test_spike_rejected_without_persistent_isolation(self):
        result=run('spikes',1001)
        for r in result['rows']:
            if r['time_s'] in (90,120,150):
                self.assertEqual(r['isolated'],[])
                self.assertEqual(len(r['selected']),2)

    def test_reproducible_and_no_oracle_input(self):
        a=run('bias',1001); b=run('bias',1001)
        self.assertEqual(a,b)
        self.assertLess(score(a)['common_rmse'], score(a)['common_median_rmse'])


if __name__=='__main__': unittest.main()
