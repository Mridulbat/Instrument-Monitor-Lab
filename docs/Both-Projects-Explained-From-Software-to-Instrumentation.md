# Both projects explained: from software to instrumentation

This guide explains the versions built before the new measurement-reliability review. The tank project remains a control study; the monitor is the calibration, diagnostic and alarm system that motivated the review.

## 1. Start with the difference between the two jobs

Imagine a tank receiving water through a controllable inlet and losing water through a drain. You want its level to remain near one metre.

**Tank Control Lab asks: what inlet flow should we command to achieve that target?** It changes the simulated process.

**Instrument Monitor Lab asks: can we trust this reading, and what should the alarm state be?** It observes measurements. It does not command the tank or shut equipment down.

For a software analogy, the first is a feedback policy that continually changes a system's input. The second is a stateful data-validation and observability service. The engineering challenge is that the data describes a changing physical process, and a plausible number is not necessarily a trustworthy measurement.

Everything here runs in software. In a physical installation, sensors, wiring, transmitters, valves and controllers would replace some simulated components. The dashboard is only the user interface; it is not the physical controller.

## 2. The small vocabulary you need

| Term | Meaning in this project | Software-friendly interpretation |
|---|---|---|
| Plant | The tank and its inlet/outlet behavior | The stateful system being acted upon |
| Setpoint | Desired level, such as 1 m | Target state |
| Process variable | Liquid level | The quantity being regulated |
| Measurement | Sensor-reported level | An observation that can be noisy or delayed |
| Manipulated variable | Inlet flow | The input the controller can change |
| Actuator | Inlet-flow mechanism | The component that applies a command, with limits |
| Disturbance | Additional water leaving the tank | An external change the controller must handle |
| Controller | PI calculation | A repeated decision algorithm |
| Calibration | Relating raw current to engineering units | A fitted measurement conversion |
| Quality | Whether the measurement is usable | Validity state, separate from the numerical value |

The distinction between **true state** and **measurement** is essential. The simulator knows the true level because it calculates it. The controller sees only the simulated sensor reading. In a real installation, the true value usually is not available directly.

## 3. Tank Control Lab: the physical model

The tank model starts with conservation of volume:

```text
change in stored volume = volume entering - volume leaving
```

For a constant-area tank, volume = area × level. Therefore:

```text
level rate = (inlet flow - outlet flow) / tank area
```

Your tank area is 0.5 m². If the inlet supplies 0.02 m³/s and the outlet removes 0.01 m³/s, the net flow is 0.01 m³/s. The level then rises at 0.01 / 0.5 = 0.02 m/s. Over 0.2 seconds, that is approximately 0.004 m.

The code's gravity-drain approximation is:

```python
outflow = 0.012 * drain_factor * sqrt(level) + extra_drain
```

The square root makes the plant nonlinear: doubling level does not double drainage. `drain_factor` represents uncertainty in the actual drain. It does not change the controller's nominal model.

The model is deliberately limited. It does not simulate detailed fluid motion, pipe pressure waves, or a measured valve characteristic. Level is clipped to 0–1.5 m. Excess above the upper bound is counted as simulated overflow; at the empty boundary, requested drainage is not necessarily physically available.

## 4. Turning continuous motion into a Python loop

Water changes continuously. A computer advances the model in discrete time steps:

```python
next_level = level + dt * (inlet_flow - outlet_flow) / area
```

This is forward Euler integration. `dt` is simulated elapsed time per update, not how long the Python program sleeps. A 600-second experiment can execute much faster than ten real minutes.

At the default `dt = 0.2`, there are 3,000 update intervals and 3,001 recorded endpoints. Every iteration computes the sensor observation, controller command, physical flow and next tank level.

Smaller steps usually approximate the continuous model more closely but require more computation. A convergence study reruns the same problem at different steps and asks whether the conclusions change. Your study uses 0.4, 0.2, 0.1 and 0.05 seconds. The finest step is a comparison reference, not proof of an exact answer.

## 5. Why feedback is needed

Suppose you choose one inlet flow and never inspect the level. It may balance the drain at one operating point, but an extra drain or a different target can destroy that balance. This is open-loop operation.

Feedback repeatedly measures the outcome and corrects the command:

```text
target → compare with measured level → controller → inlet → tank → sensor
                       ↑________________________________________|
```

The error is:

```python
error = target - measured_level
```

For target 1 m and measurement 0.8 m, error is +0.2 m. The controller should generally request more inlet flow. For measurement 1.1 m, error is −0.1 m, so it should reduce flow.

## 6. Proportional and integral control

The proportional term responds to the current error:

```python
p_term = kp * error
```

With `kp = 0.025` and error 0.2 m, it contributes 0.005 m³/s. A higher gain reacts more strongly; this can reduce sluggishness but can also increase oscillation, especially with delay.

The integral term accumulates error over time:

```python
integral += ki * error * dt
```

Think of it as a memory of persistent mismatch. Even if the current error is small, an error that persists contributes repeatedly. This helps remove a sustained offset when the system has sufficient actuation and suitable tuning.

With `ki = 0.001`, error 0.2 m and `dt = 0.2`, one update adds 0.00004 m³/s to the integral correction. These units matter: the integral variable is a flow correction, not an arbitrary counter.

The controller is **PI**, not full PID: there is no derivative term. Derivative action responds to a rate of change, but it was not required for this study and would introduce filtering and noise considerations. The general controller terms are described in the [MathWorks PID introduction](https://www.mathworks.com/discovery/pid-control.html).

## 7. Feedforward: use the model before waiting for error

The controller can estimate the nominal flow needed to balance the drain at the desired level:

```python
bias = 0.012 * sqrt(target)
command = bias + kp * error + integral
```

At a 1 m target, nominal drainage is 0.012 m³/s, so feedforward supplies that baseline. Feedback then corrects mismatch around it.

This is not a prediction of every future disturbance. It is compensation based on the nominal model and requested level. If actual drainage differs, the bias will be imperfect.

PI-only configurations begin with an integral equal to nominal initial drain flow. Feedforward configurations begin with zero integral. This gives both the same initial nominal equilibrium rather than unfairly starting one with no balancing flow.

## 8. Saturation and anti-windup

The inlet can only deliver 0–0.04 m³/s:

```python
command = min(0.04, max(0, requested_flow))
```

Suppose the controller requests 0.08 m³/s. The actuator still delivers at most 0.04. If positive error persists, the integral can keep increasing even though the additional command has no effect. That accumulation is windup.

Later, when the level reaches its target, the large stored integral can keep the inlet too open. The tank overshoots.

Your implementation uses conditional integration. It refuses an integral update if the proposed command is beyond a limit and the error would push it further beyond that limit. Updates that help leave saturation remain allowed. This is why anti-windup is more specific than simply clamping every internal variable. See the [MathWorks anti-windup example](https://www.mathworks.com/help/simulink/slref/anti-windup-control-using-a-pid-controller.html).

## 9. Lag, delay and uncertainty

**Actuator lag:** the flow does not instantly equal the command. A first-order response gradually approaches it. With a three-second time constant, a held step reaches approximately 63% of its eventual change after three seconds.

**Sensor delay:** the controller receives an old level. A two-second delay means it reacts to where the tank was two seconds earlier. Strong correction based on old information can produce oscillation.

**Sensor noise:** random measurement variation is added. A fixed random seed lets different controllers face the same realization.

**Drainage uncertainty:** the actual drain coefficient is multiplied by a factor such as 1.2, while feedforward continues using the nominal coefficient. This tests model mismatch.

These additions make the controller study more meaningful because the algorithm must be judged under imperfect information and non-instantaneous action.

## 10. Reading the tank results

The standard timeline is: target rises at 30 seconds, extra drainage starts at 300 seconds, and extra drainage stops at 450 seconds.

| Metric | What it tells you |
|---|---|
| IAE | Total absolute tracking error accumulated over time; lower is better for an otherwise identical experiment |
| Overshoot | How far level rises beyond target, normalized here by the 0.6 m target step |
| Settling time | How long it takes to remain inside the specified tolerance during the observation interval |
| Saturation duration | How long the controller asks beyond the actuator limits |
| Overflow | Calculated volume exceeding the tank's upper bound |

Your settling criterion is ±0.012 m, which is 2% of the 0.6 m step. It is evaluated before the later disturbance with at least 20 seconds of remaining observation. This finite-window metric is not a stability proof.

The 576-run study compares four controller variants across gains, disturbances, noise, seeds, plant uncertainty and dynamics. The 96-run study examines time-step sensitivity. A test run count describes coverage; the resulting metrics describe behavior.

## 11. Instrument Monitor Lab: what arrives at the input

A measurement arrives as a timestamp and raw current, for example:

```python
{"time_s": 12.0, "raw_mA": 12.0}
```

The demo represents a 4–20 mA transmitter. A physical transmitter converts a measured quantity into an electrical signal; your project starts at the represented current value and has no actual wiring. A concrete hardware example is [TI's 4–20 mA transmitter reference design](https://www.ti.com/tool/TIPD158).

The existing project accepts CSV data, generated demonstration samples, or values from the local simulated Modbus device. CSV parsing checks column names, finite numbers, strictly increasing timestamps and row limits. A blank current means missing, not zero.

## 12. Calibration and what it does not prove

Five example pairs map current to reference values:

```text
4.10 mA →   0 units
8.05 mA →  25 units
12.0 mA →  50 units
15.95 mA → 75 units
19.90 mA →100 units
```

The fitted conversion is approximately:

```python
value = 6.32911 * raw_mA - 25.94937
```

Thus 12 mA maps to 50 units. This is an affine conversion: slope changes scale and intercept corrects offset.

In the existing version, these five points were constructed to lie exactly on a line. Consequently, fitting them demonstrates implementation of the conversion but provides little evidence about real calibration quality. There are no repeated laboratory measurements, reference uncertainty, or independently measured calibration errors. This distinction is central to the new review.

## 13. Quality checking happens before trusting alarms

The monitor checks several patterns:

| Check | Implemented idea | Important ambiguity |
|---|---|---|
| Missing | No current value exists | Cannot infer a healthy process from no data |
| Range | Current outside 4–20 mA | A readable number may still be electrically invalid |
| Gap | Received timestamps are more than two seconds apart | Depends on the expected sample interval |
| Stale | Heartbeat has not changed for more than two seconds | TCP can answer with old data |
| Stuck | Current stays within 0.002 mA of an anchor for eight seconds | A healthy steady process can also be constant |
| Spike | Large deviation from recent median | A genuine process step can look similar |
| Noisy | Large variation of successive differences | A real transient can disturb this statistic |
| Drift | Persistent disagreement with supplied reference | Needs an independent reference unavailable in ordinary CSV/live input |

These are rules, not machine learning. The stronger engineering question is whether their assumptions distinguish a sensor problem from a real process change. The synthetic benchmark showed that some cannot do that reliably from one signal alone.

## 14. Process alarms and measurement quality are separate states

The high alarm raises at 80 units but clears only at 77 or below. This separation is hysteresis. Without it, readings 79.9, 80.1, 79.9, 80.1 could repeatedly toggle an alarm. The low alarm raises at 20 and clears at 23 or above.

Now suppose HIGH is active and the sensor disconnects. A missing measurement does not show that the process returned below 77. Clearing HIGH would wrongly imply recovery.

The implemented state machine does this:

```text
GOOD → invalid measurement → BAD
BAD → first valid measurement → RECOVERING
RECOVERING → second consecutive valid measurement → GOOD
```

During BAD and RECOVERING, active HIGH/LOW alarms are held and QUALITY_UNKNOWN is present. Once GOOD is re-established, the normal hysteresis logic can clear an alarm if the value supports recovery. New process alarms are not inferred from bad data.

Events are emitted on transitions, not on every sample. A state that remains HIGH for 100 samples need not produce 100 identical "HIGH raised" messages.

## 15. What detection metrics actually mean

During a synthetic experiment, the generator knows when a fault was injected. The detector should receive only information that would be available to it; the evaluator can use hidden truth to score the output.

**Precision** asks: of the samples flagged as faulty, how many were truly labelled faulty? **Recall** asks: of the truly faulty samples, how many were flagged?

For example, if three real spikes are all detected but thirty healthy samples are also flagged, recall is 100% while precision is 3/33, or about 9.1%. Detecting every spike therefore does not imply a good overall detector.

**Detection delay** measures the elapsed time from fault onset until detection. An eight-second stuck window intentionally waits, so the initial faulty samples can be missed even if the event is eventually found.

The existing benchmark counts quality holds after a fault ends as false-positive samples. Those are not necessarily separate nuisance-alarm episodes. Event counts, flagged duration and sample-level metrics answer different questions and should be reported separately.

## 16. How Modbus connects the two projects

Your web dashboard uses HTTP and JSON. The industrial-style interface uses Modbus TCP: a client requests addressed registers from a device. This implementation supports function code 03, reading holding registers. See the [Modbus application protocol specification](https://www.modbus.org/file/secure/modbusprotocolspecification.pdf).

The device exposes six unsigned 16-bit registers: level, inlet flow, current signal, actuator command, heartbeat and device quality. Integer scaling represents fractional quantities. A level of 0.4 m becomes integer 4000, then the client divides by 10,000.

The tank device precomputes a trajectory from the same tank engine and serves points according to elapsed wall-clock time. It loops the 600-second trace. Dashboard tuning runs do not automatically retune this separate device, and the monitor sends no commands back.

The heartbeat changes once per second. If it stops changing, the client marks communication data stale even if network reads succeed. The freeze demonstration deliberately stops the device's values and heartbeat. This models the difference between "the connection works" and "the process data is fresh."

## 17. Reading the architecture like a software developer

The numerical/diagnostic engine contains the core functions. The HTTP handler validates requests and invokes the engine. The HTML/JavaScript interface collects settings, draws returned data and downloads exports. Benchmark scripts generate controlled cases and save measured results. Unit and integration tests exercise model invariants, state transitions, parsing and protocol behavior.

Keeping the engine separate allows the same logic to be tested without a browser. There is no database because this is a local, bounded experiment. No cloud service is needed. The live monitor retains a bounded history and reprocesses it; it is not an unlimited historian.

Tests check specific claims, such as "missing data must not clear HIGH" or "actuator flow cannot exceed its limit." A passing test suite does not establish industrial safety, physical calibration accuracy, or correct behavior for every possible signal.

## 18. How to build understanding by running the projects

1. Run the tank with default settings. Identify the target change and disturbance interval.
2. Increase proportional gain and predict the response before running.
3. Increase integral gain, toggle anti-windup, and inspect flow as well as level.
4. Add actuator lag and sensor delay. Explain why reacting more strongly can now make behavior worse.
5. Open the monitor. Trace 12 mA through calibration to 50 units.
6. Follow HIGH, missing data, RECOVERING and GOOD in the alarm logic.
7. Start the local Modbus device and inspect scaled register values.
8. Freeze its heartbeat and explain why stale data is not the same as a disconnected socket.
9. Read the benchmark tables. Identify both a successful result and a case where the method fails.

You are ready to defend these projects when you can explain a change in the plot from the equations or state transitions, and when you can explain what evidence would be required before applying the same method to real equipment.

For a short recall exercise, open [the first checkpoint](learning-guide/lessons/0001-control-and-measurement.html).
