import unittest
from src.engine import calibrate, parse_csv, analyze, demo_data


class MonitorTests(unittest.TestCase):
    def test_calibration(self):
        slope, intercept = calibrate([4.1,12,19.9],[0,50,100])
        self.assertAlmostEqual(slope*12+intercept,50)
        with self.assertRaises(ValueError): calibrate([4,4],[0,100])

    def test_fault_detection(self):
        events = analyze()['events']
        raised={(e['time_s'],e['event']) for e in events if e['state']=='RAISED'}
        for pair in [(110,'MISSING'),(158,'STUCK'),(250,'RANGE')]:
            self.assertIn(pair,raised)

    def test_hysteresis(self):
        readings=[79,81,79,78,76]
        rows=[{'time_s':i,'raw_mA':4.1+.158*v} for i,v in enumerate(readings)]
        events=analyze(rows)['events']
        self.assertEqual([(e['time_s'],e['state']) for e in events if e['event']=='HIGH'],[(1,'RAISED'),(4,'CLEARED')])

    def test_missing_resets_stuck(self):
        rows=[{'time_s':i,'raw_mA':None if i==5 else 12} for i in range(14)]
        self.assertFalse(any(e['event']=='STUCK' for e in analyze(rows)['events']))

    def test_gap_resets_stuck(self):
        result=analyze([{'time_s':0,'raw_mA':12},{'time_s':20,'raw_mA':12}])
        self.assertIn('GAP',result['rows'][-1]['flags'])
        self.assertNotIn('STUCK',result['rows'][-1]['flags'])

    def test_csv(self):
        rows=parse_csv('time_s,raw_mA\n0,4.1\n1,\n2,19.9\n')
        self.assertIsNone(rows[1]['raw_mA'])
        self.assertEqual(analyze(rows)['metrics']['Samples'],3)

    def test_rejects_bad_input(self):
        for data in ['x,y\n1,2','time_s,raw_mA\n0,nan','time_s,raw_mA\n1,4\n1,5','time_s,raw_mA\n']:
            with self.assertRaises(ValueError): parse_csv(data)
        with self.assertRaises(ValueError): analyze(low=90,high=80)

    def test_all_missing(self):
        result=analyze([{'time_s':i,'raw_mA':None} for i in range(10)])
        self.assertEqual(result['metrics']['Valid samples (%)'],0)
        self.assertIsNone(result['metrics']['Reference RMSE'])
        self.assertEqual(len(result['events']),2)

    def test_no_false_faults_on_normal_demo(self):
        rows=[r for r in demo_data() if r['time_s']<60]
        self.assertFalse(analyze(rows)['events'])


if __name__ == '__main__': unittest.main()
