"""Synthetic sample-level and event-level diagnostic evaluation."""
import csv
import json
import math
import random
from pathlib import Path
from src.engine import analyze

ROOT=Path(__file__).resolve().parent
KINDS=['normal','healthy_step','drift','drift_unreferenced','spikes','noisy','dropouts','irregular','stuck','range']
FAULT_FLAGS={'MISSING','RANGE','GAP','STUCK','STALE','SPIKE','NOISY','DRIFT','QUALITY_UNKNOWN'}

def scenario(kind,seed):
    rng=random.Random(seed);rows=[];frozen=12.0
    for t in range(301):
        truth=50+2*math.sin(t/25)
        if kind=='healthy_step' and 100<=t<200:truth+=30
        raw=4.1+.158*truth+rng.gauss(0,.015);fault=False
        if 100<=t<200:
            if kind in ('drift','drift_unreferenced'):raw+=.158*.1*(t-100);fault=True
            elif kind=='spikes' and t in (110,140,170):raw+=.158*25;fault=True
            elif kind=='noisy':raw+=.158*rng.gauss(0,6);fault=True
            elif kind=='dropouts' and t%20<5:raw=None;fault=True
            elif kind=='irregular':
                if t%10 in (1,2,3):continue
                fault=t%10==4
            elif kind=='stuck':raw=frozen;fault=True
            elif kind=='range':raw=22;fault=True
        row=dict(time_s=t,raw_mA=raw,fault=fault)
        if kind!='drift_unreferenced':row['reference']=truth
        rows.append(row)
    return rows

def score(rows):
    detected=[bool(set(r['flags'].split('|'))&FAULT_FLAGS) for r in rows]
    truth=[r['fault'] for r in rows]
    tp=sum(a and b for a,b in zip(truth,detected));fp=sum(not a and b for a,b in zip(truth,detected));fn=sum(a and not b for a,b in zip(truth,detected))
    intervals=[];start=None
    for i,fault in enumerate(truth+[False]):
        if fault and start is None:start=i
        if not fault and start is not None:
            hits=[j for j in range(start,i) if detected[j]]
            intervals.append(None if not hits else rows[hits[0]]['time_s']-rows[start]['time_s']);start=None
    delays=[d for d in intervals if d is not None]
    return dict(tp=tp,fp=fp,fn=fn,precision=round(tp/(tp+fp),4) if tp+fp else None,recall=round(tp/(tp+fn),4) if tp+fn else None,fault_events=len(intervals),detected_events=len(delays),mean_delay_s=round(sum(delays)/len(delays),2) if delays else None,false_alarm_samples=fp,normal_samples=sum(not x for x in truth))

def main():
    records=[]
    for kind in KINDS:
        for seed in [7,11,19,41,73]:
            result=analyze(scenario(kind,seed));records.append(dict(scenario=kind,seed=seed,**score(result['rows'])))
    output=ROOT/'examples'
    with (output/'fault-benchmark.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
    summary=[]
    for kind in KINDS:
        rows=[r for r in records if r['scenario']==kind];tp=sum(r['tp'] for r in rows);fp=sum(r['fp'] for r in rows);fn=sum(r['fn'] for r in rows)
        delays=[r['mean_delay_s'] for r in rows if r['mean_delay_s'] is not None]
        summary.append(dict(scenario=kind,tp=tp,fp=fp,fn=fn,precision=round(tp/(tp+fp),3) if tp+fp else None,recall=round(tp/(tp+fn),3) if tp+fn else None,mean_run_delay_s=round(sum(delays)/len(delays),2) if delays else None,events=sum(r['fault_events'] for r in rows),detected_events=sum(r['detected_events'] for r in rows)))
    report=dict(runs=len(records),seeds=[7,11,19,41,73],summary=summary,definition='Sample-level binary quality detection; process HIGH/LOW excluded. Event detection must occur inside the injected interval. Delays only for detected events. Drift uses independent synthetic reference except drift_unreferenced.');(output/'benchmark-summary.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

if __name__=='__main__':main()
