"""Refresh numerical documentation and plots from saved study evidence (matplotlib optional dependency)."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT/'docs'
EVIDENCE = ROOT/'examples/study'
data = json.loads((EVIDENCE/'summary.json').read_text())
summary = {s['scenario']:s for s in data['summary']}
fmt = lambda x: 'N/A' if x is None else f'{x:.3f}'
pct = lambda x: 'N/A' if x is None else f'{100*x:.1f}%'
bias = summary['bias']
improvement = 100*(1-bias['common_rmse']/bias['common_median_rmse'])

plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig, axes = plt.subplots(1,2,figsize=(10,4.8))
for ax, kind in zip(axes, ('drift','dual_fault')):
    rows=json.loads((EVIDENCE/f'{kind}-1001.json').read_text())['rows']
    t=[r['time_s'] for r in rows]
    for i in range(3): ax.plot(t,[r['values'][i] for r in rows],color='#b4c2cb',lw=.7)
    ax.plot(t,[r['truth'] for r in rows],color='#163349',label='Truth (evaluation only)')
    ax.plot(t,[r['value'] for r in rows],color='#087e8b',label='Consensus',lw=1.4)
    ax.set(title=kind.replace('_',' ').title(),xlabel='Time (s)',ylabel='Engineering units')
axes[0].legend(fontsize=8); fig.tight_layout(); fig.savefig(DOCS/'study-traces.png',dpi=160);plt.close(fig)
fig,axes=plt.subplots(1,2,figsize=(10,4.8))
kinds=['healthy','bias','drift','frozen','high_noise']
for offset,key,label,color in [(-.18,'common_rmse','Consensus','#087e8b'),(.18,'common_median_rmse','Median','#ae3170')]:
    axes[0].bar([i+offset for i in range(len(kinds))],[summary[k][key] for k in kinds],width=.35,label=label,color=color)
axes[0].set_xticks(range(len(kinds)),[k.replace('_','\n') for k in kinds]);axes[0].set_ylabel('RMSE on common valid samples');axes[0].legend()
readings=json.loads((EVIDENCE/'calibration-readings.json').read_text())
models=json.loads((EVIDENCE/'drift-1001.json').read_text())['calibrations']
for i,(samples,c) in enumerate(zip(readings,models)):
    axes[1].scatter([s['reference'] for s in samples],[s['current']-c['intercept']-c['slope']*s['reference'] for s in samples],s=12,label='ABC'[i],alpha=.7)
axes[1].axhline(0,color='grey',lw=.7);axes[1].set(xlabel='Reference (engineering units)',ylabel='Forward fit residual (mA)');axes[1].legend();fig.tight_layout();fig.savefig(DOCS/'study-results.png',dpi=160);plt.close(fig)

sections=[]
def section(title,*blocks): sections.append(dict(title=title,blocks=list(blocks)))
section('Problem and original limitations',
 ['p','The original monitor converts current to engineering units, checks temporal signal quality, and manages process alarms. Its architecture, missing-data handling, hysteresis and tests remain useful. Its perfectly collinear calibration points, however, do not demonstrate calibration error characterisation. A single signal cannot reliably distinguish genuine process drift from sensor drift.'],
 ['p','The original 50-run benchmark remains reproducible with benchmark.py. It records 100 false-positive samples on healthy steps, 9.1% sample precision for spikes, and no detected unreferenced drift events. These results motivated a change in information available to the detector, rather than adding more dashboard features.'],
 ['p','New problem: can three independently calibrated instruments provide a defensible measurement when one instrument becomes unreliable? The output includes uncertainty, quality, persistent isolation and process-alarm state. All evidence is synthetic; there is no hardware or industrial validation.'])
section('Decision and alternatives',
 ['table',[['Approach','Value / limitation','Decision'],['Calibration analytics only','Quantifies error; does not resolve process/fault ambiguity','Supporting layer'],['Temporal thresholds or CUSUM','Needs a trustworthy baseline or process model','Legacy comparator retained'],['Tank observer','Useful but requires validated flows and model uncertainty','Deferred'],['Three independent instruments','Makes single-channel disagreement observable','Selected'],['ML, cloud, more protocols','Does not fix missing diagnostic information','Excluded']]],
 ['p','The alternatives and selected design were recorded in decision-record.md before implementation. Thresholds were chosen before the held-out evaluation and were not retuned after inspecting results. Later observations about common-mode failures and elevated noise are validation findings, not claims that these choices were experimentally optimal.'],
 ['p','Added redundancy is a real assumption and cost. The single-channel comparison cannot establish an algorithm-only improvement. The three-channel median baseline receives the same additional currents and is the main measurement-quality comparator.'])
section('Architecture and input contract',
 ['flow',['Raw currents|A / B / C','Inverse|calibration','Pairwise|agreement','Quality and|isolation','Estimate and|alarms']],
 ['p','calibration.py fits and inverts each transmitter. validation.py receives only timestamp, three currents, three reported ages and calibration models. study.py generates synthetic inputs, runs the detector, then attaches truth and fault labels for scoring. The detector never receives truth or labels. study_benchmark.py writes per-run scores and scenario aggregates.'],
 ['p','The existing engine.py, CSV upload, event log and one-channel Modbus client remain available at /. The new study is at /study.html and POST /api/study. The six existing Modbus registers do not represent three independent instruments; they are not used as evidence for redundancy.'],
 ['p','Timestamps must be finite, nonnegative and strictly increasing. Inputs require exactly three currents and ages. Missing, nonfinite, out-of-range, negative-age or stale channels are unavailable. A timestamp gap over 2 seconds invalidates the current batch; recovery requires two consecutive usable batches. Known age greater than 2 seconds is stale. Hidden skew is not automatically corrected.'])
section('Calibration mathematics and uncertainty',
 ['p','For each channel, fit I = a + b*x + epsilon using ordinary least squares, where I is current in mA and x is the reference in 0-100 engineering units. Six levels with five repeats produce 30 observations per channel. Calibration seeds are 101, 102 and 103. Noise standard deviation is 0.032 mA; transmitter (a,b) pairs are (4.10,0.158), (4.04,0.159), (3.98,0.160).'],
 ['p','The measurement is x_hat = (I-a)/b. With residual variance s^2 = SSE/(n-2), Sxx = sum((x-x_bar)^2), the independent inverse variance is [s^2 + s^2*(1/n + (x_hat-x_bar)^2/Sxx)]/b^2. This is first-order propagation of repeatability and fit-coefficient covariance. It assumes affine response, independent approximately Gaussian current errors, negligible slope uncertainty beyond first order, and accurate reference levels for the fit.'],
 ['p','A shared reference standard uncertainty of 0.05 units is an explicit assumed budget allowance. It is not estimated from physical calibration equipment. Consensus over m selected channels uses U = 2*sqrt(sum(u_independent^2)/m^2 + u_reference^2). The shared term does not shrink with averaging and cancels in pairwise differences. Equal weighting avoids pretending the small repeatability estimates justify precise reliability weights.'],
 ['p','Electrical acceptance is 3.8-20.5 mA, followed by a calibrated-span gate with a 1-unit endpoint allowance for noisy readings. This is an educational choice, not a claimed industrial standard. Zero residual variance is rejected because it cannot support this empirical noise budget. k=2 bands are approximate, not exact 95% prediction intervals.'],
 ['p','Methods reference: <link href="https://www.itl.nist.gov/div898/handbook/mpc/section3/mpc366.htm" color="#087e8b">NIST inverse calibration</link> and <link href="https://www.itl.nist.gov/div898/handbook/pmd/section5/pmd521.htm" color="#087e8b">NIST calibration uncertainty</link>.'])
section('Agreement, isolation and alarm decisions',
 ['p','Channels i and j agree when |xi-xj| is no larger than max(0.5 units, 4*sqrt(ui^2+uj^2)), using independent variances. The 4-standard-uncertainty threshold deliberately favours low nuisance isolation; it does not imply a system-wide Gaussian false-alarm probability after repeated testing. The floor prevents implausibly tight agreement at very low estimated noise.'],
 ['table',[['Evidence','Action'],['All three pairs agree','Use arithmetic mean of three'],['Exactly one pair agrees','Use that pair; third available channel is suspect'],['Two agreeing edges, or no pair','Ambiguous; output UNKNOWN'],['Only one available channel','Insufficient redundancy; UNKNOWN'],['Same suspect for 3 consecutive samples','Report isolated channel'],['Agreement recovers','Reset isolation immediately; no repair acknowledgement model']]],
 ['p','Suspect channels are excluded from the estimate immediately; persistent isolation is a separate decision. One-sample spikes therefore can be rejected without being classified as persistent faults. An UNKNOWN interval restarts the two-sample quality recovery. With a usable pair, quality is DEGRADED; all three agreeing gives CONSISTENT. Neither word proves health.'],
 ['p','HIGH raises when the lower uncertainty bound reaches 80 and clears only when the upper bound reaches 77 or less. LOW raises when the upper bound reaches 20 or less and clears when the lower bound reaches 23. Ambiguous bounds and unknown quality hold previous alarm state. This delays declarations until measurement evidence supports them; it is educational logic, not a fail-safe action or a safety-system design.'])
section('Reproducible experiment design',
 ['p',f'{data["run_count"]} runs cover 16 scenarios with 20 withheld seeds (1001-1020), each lasting 240 seconds with nominal 1-second samples. Calibration seeds are separate. Seeds 7 and 11 are reserved for development and are not included in the published study. Bias/drift magnitude varies uniformly from 5 to 10 units; the affected channel rotates by seed modulo 3. Faults generally occur from 80 to 179 seconds inclusive.'],
 ['p','Scenarios: healthy sinusoid, common step, stable plateau, drift, bias, isolated spikes, noisy sensor, frozen sensor, intermittent dropout, irregular sampling, stale channel, all channels missing, common-mode bias, two agreeing faulty sensors, hidden 8-second skew, and increased noise on all sensors. Complete formulas are in study.generate; representative raw currents, ages and labelled traces are saved for seed 1001.'],
 ['p','Baseline 1 applies the original temporal logic to calibrated channel A without a truth reference. Inputs are converted back to its nominal current convention so differences are not simply calibration offsets. Its information is less than the new detector; faults rotate across channels, so some faults do not affect A. Baseline 2 is the median of electrically/calibration-valid readings without age, agreement or recovery gating.'],
 ['p','Independent calibration validation uses 10 withheld levels (5,15,...95), 100 readings per level and seeds 9001-9003: 3,000 samples. This is validation under the assumed linear/noise model, not evidence of real sensor linearity. The shared reference allowance is included in intervals but a shared physical reference bias is not randomly injected.'])
section('Metrics and fair comparisons',
 ['p','Sample diagnosis is a union of explicit invalidity and persistent isolation, matched to channel-specific injection labels. Precision = TP/(TP+FP), recall = TP/(TP+FN). A fault event is a contiguous labelled interval for one channel; detection must occur inside that interval. Delay is elapsed time to first diagnosis and is reported only for detected events. Missed events are shown explicitly.'],
 ['p','false_episodes counts contiguous false diagnosis episodes, including quality invalidations. false_isolation_episodes counts only persistent isolation of unlabelled channels. In irregular sampling, no sensor fault is labelled: the 360 conservative gap invalidations count as false diagnoses, but there are zero false sensor-isolation episodes. This distinction avoids calling communication caution a sensor fault.'],
 ['p','Output RMSE is measured on accepted samples and must be read with availability. Median and consensus are also compared on identical common valid timestamps within each run. Tables report the mean of per-run RMSE, not a pooled RMSE; availability and uncertainty coverage are pooled sample fractions. Coverage counts truth within the reported k=2 band, conditional on an available output.'],
 ['p','Do not collapse all scenarios into one accuracy number. Multi-fault and noise-mismatch cases violate key assumptions and expose failure envelopes. Precision/recall are undefined when their denominators are zero and are reported N/A. Three-sample persistence at 1 Hz creates a nominal 2-second bias diagnosis delay; this is not a universal real-time guarantee.'])
table=[['Channel','Validation samples','RMSE (units)','Max error','k=2 coverage']]
for c in data['calibration_validation']: table.append(['ABC'[c['channel']],c['samples'],fmt(c['rmse']),fmt(c['max_abs_error']),pct(c['coverage'])])
section('Calibration validation results',['table',table],['image','study-results.png'],
 ['p','Residuals reveal the scatter that the original exactly collinear calibration omitted. The nominal validation coverages are near 95%, but small calibration samples and unmodelled nonlinearity/reference bias limit that interpretation. The high-noise experiment shows that a nominal uncertainty budget cannot be trusted after operating noise changes.'])
for title,kinds in [('Nominal and single-fault results',['healthy','step','plateau','drift','bias','spikes','noise','frozen','dropout','stale']),('Failure-envelope results',['irregular','all_missing','common_mode','dual_fault','misaligned','high_noise'])]:
    table=[['Scenario','Events hit / total','Delay s','Recall','Available','Coverage']]
    for k in kinds:
        s=summary[k];table.append([k.replace('_',' '),f'{s["detected"]}/{s["events"]}',fmt(s['mean_delay']),pct(s['recall']),pct(s['availability']),pct(s['coverage'])])
    section(title,['table',table],['p','Full precision, false diagnoses, false isolations, per-run scores, common-sample errors and baseline availability are saved in examples/study/summary.csv and run-scores.json. Events with no detection have N/A delay. Spikes are excluded from consensus immediately but deliberately do not satisfy persistent isolation; zero event recall must not be described as complete spike diagnosis.'])
section('Measured improvement and trade-offs',
 ['p',f'For bias, all {bias["detected"]}/{bias["events"]} injected events were diagnosed with a mean delay of {bias["mean_delay"]:.1f} seconds. Common-sample RMSE fell from {bias["common_median_rmse"]:.4f} for the median to {bias["common_rmse"]:.4f} units for consensus: a {improvement:.1f}% reduction. Availability was {pct(bias["availability"])}; sample recall was {pct(bias["recall"])} because of persistence and occasional disagreement ambiguity.'],
 ['p','Across healthy, step and plateau experiments there were zero false sensor-isolation episodes in 60 runs. The healthy-step comparison recorded 400 quality-flagged legacy samples versus zero false isolations in the new method. These are different diagnostic outputs, not interchangeable accuracy rates. Consensus availability remained 99.5%, not 100%, because ambiguous agreement and startup recovery can suppress output.'],
 ['p','Drift detection took 21.15 seconds on average and had 78.05% sample recall: small drift initially remains indistinguishable from noise. Frozen detection averaged 5.3 seconds and depends on the process moving away from the frozen value. A truly stationary process cannot identify a perfectly agreeing frozen instrument.'],
 ['image','study-traces.png'])
section('Limits, exclusions and engineering judgement',
 ['p','Common-mode bias produced zero diagnosed events and about 4.65 units RMSE while consensus remained available. Two faulty sensors agreeing with each other caused the healthy channel to be isolated in 20 runs. Redundancy needs independence, physical diversity and common-cause assessment; counting sensors alone does not provide reliability assurance.'],
 ['p','With elevated noise on all channels, availability fell to 80.8%, k=2 coverage to 75.9%, and common-sample RMSE worsened to 0.438 versus the median baseline at 0.393 units. A recalibrated noise budget or explicit adaptive uncertainty model is future work; retuning after seeing these results would require fresh validation seeds.'],
 ['p','Hidden timestamp skew can resemble a sensor fault. The project checks reported age but does not synchronize devices or estimate network latency. Calibration linearity, physical reference uncertainty, sensor independence, error distributions, numerical thresholds and alarm setpoints are assumptions. No physical units beyond a generic engineering scale are claimed.'],
 ['p','Excluded: ML, cloud deployment, new protocols, hardware procurement, a process observer, automated sensor repair, SIL/IEC compliance claims, safety actuation and physical commissioning. The existing Modbus interface remains an educational loopback demonstration.'])
section('Reproduce, inspect and explain',
 ['p','Application: python src/server.py, then open /study.html. Choose bias, drift, common_mode and dual_fault in that order. Export JSON and inspect isolated, selected, invalid, quality, expanded_u, high and low for each timestamp. Then compare high_noise against healthy.'],
 ['p','Checks: python -m unittest discover -s tests -v. Evidence: python study_benchmark.py. Legacy comparison: python benchmark.py. Refresh figures and numerical report source: python docs/refresh_study_docs.py (matplotlib required). Rebuild PDF: python docs/build_report.py (ReportLab required). The application, automated tests and benchmarks use the standard library only.'],
 ['p','A software-focused explanation: calibration is a noisy coordinate transform with an error budget; the validator is a state machine constrained by measurement evidence; the test bench is a fault-injection harness with labels kept separate from production inputs. The engineering contribution is choosing what the system can infer and testing when those inferences fail.'],
 ['p','Interview exercise: explain why a median already handles one large outlier; why consensus improves bias error yet can reduce availability; why uncertainty does not average down for shared reference error; and why two agreeing bad sensors can defeat the algorithm. Verification records and resume bullets are saved separately in docs.'])
report=dict(title='Instrument Measurement Validation',subtitle='Uncertainty-aware calibration, redundant sensor agreement and reproducible fault-injection evidence',number='02',flow=['Calibrate','Compare','Diagnose','Validate'],sections=sections)
(DOCS/'report-source.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
lines=['# Instrument Measurement Validation — engineering report','\nUpdated 22 October 2026. All results are simulated.\n']
for s in sections:
    lines.append('\n## '+s['title']+'\n')
    for kind,body in s['blocks']:
        if kind in ('p','h'): lines.append(body+'\n')
        elif kind=='table':
            lines.append('| '+' | '.join(map(str,body[0]))+' |');lines.append('| '+' | '.join(['---']*len(body[0]))+' |')
            for row in body[1:]: lines.append('| '+' | '.join(map(str,row))+' |')
            lines.append('')
        elif kind=='image': lines.append(f'![Study result]({body})\n')
        elif kind=='flow': lines.append(' → '.join(body)+'\n')
(DOCS/'engineering-study.md').write_text('\n'.join(lines),encoding='utf-8')
bullets=f'''# Verified resume evidence

Suggested title: **Instrument Calibration & Measurement Validation | Python, Instrumentation, Fault Diagnosis**

- Developed uncertainty-aware validation for three simulated instrument channels, reducing measurement RMSE against a median baseline under single-sensor bias by **{improvement:.1f}%**.
- Built a reproducible fault-injection test bench covering drift, bias, frozen signals, dropouts and common-cause failures across **16 scenarios and 320 runs**.
- Fitted and independently validated three transmitter calibrations, achieving simulated measurement RMSE of **0.192–0.217 units across 3,000 validation readings**.

Every claim is simulation-only. RMSE reduction uses common valid timestamps in 20 bias runs: {bias['common_median_rmse']:.6f} → {bias['common_rmse']:.6f}. Calibration RMSE values come from examples/study/summary.json. Do not claim physical calibration, commissioning or industrial fault-detection accuracy. Keep limitations in the report and discuss them in interviews; resume bullets need not list every failure mode.
'''
(DOCS/'resume-bullets.md').write_text(bullets,encoding='utf-8')
print('Refreshed report source, engineering-study.md, resume bullets and two figures.')
