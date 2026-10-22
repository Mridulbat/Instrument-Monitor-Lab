# The upgraded monitor, from a software perspective

The earlier two-project walkthrough explains the original monitor and Tank Control Lab. This adds the new measurement-validation layer.

Imagine three instruments measuring the same vessel. Each sends a current. Their currents differ slightly even when the true quantity is identical because each has an offset, sensitivity and measurement noise. Here the quantity is a generic 0–100 scale; no real hardware is involved.

## Calibration learns a coordinate system

Give each simulated instrument known reference values and record the resulting currents. Six levels and five repeats produce 30 points. Fit current = offset + sensitivity × reference, then invert that relation to convert future currents back to engineering units.

This is regression with a physical meaning. The controlled reference is the input; current is the noisy output. Residuals estimate repeatability and uncertainty in the fitted line. A perfect artificial straight line cannot tell you how noisy a real reading will be.

## A measurement needs an error budget

50.0 does not imply exact knowledge of the true quantity. The project combines current noise, calibration-fit uncertainty and an assumed shared reference uncertainty of 0.05 units. Independent noise partially averages out; shared reference error does not. If the reference is biased, every calibrated instrument can be biased together.

The reported interval uses k=2, an approximate multiplier. The evaluator checks how often that interval actually contains simulated truth. It is not a certified accuracy specification.

## Agreement supplies information that one trace lacks

Suppose the readings are 50.1, 49.9 and 58.0. The first two agree within uncertainty. Under the single-fault assumption, use that pair and mark the third suspect. Three consecutive disagreements produce persistent isolation.

If all three jump from 50 to 85 together, that supports a genuine process change. A one-sensor spike rule cannot use that additional evidence. The engineering improvement comes from information, not code length.

If readings form an ambiguous chain where A agrees with B and B agrees with C but A disagrees with C, no unique pair is justified. This implementation returns UNKNOWN. That costs availability but avoids choosing whichever pair looks convenient.

## Estimation and diagnosis have different timing

An outlier is excluded immediately, but persistent isolation requires three samples. At one sample per second, the third arrives two seconds after the first. One-sample spikes can therefore be excluded without generating persistent isolation. Zero persistent spike-event recall does not mean every spike passes into the estimate.

## Unknown does not mean safe

Missing, stale or inconsistent readings can leave no trusted estimate. Existing alarms are held through unknown quality; two usable batches are needed for recovery. To raise HIGH at 80, the lower uncertainty bound must reach 80. To clear HIGH, the upper bound must fall to 77 or less. This demonstrates an explicit policy; a real plant needs hazard-driven alarm and safety design.

## Keep evaluation truth outside the algorithm

The generator knows the process truth and injected faults. The validator receives only currents, timestamps, reported ages and calibration models. Only afterward does the evaluator compare outputs with truth. This is analogous to keeping test labels out of a prediction API.

## Beat a meaningful simple baseline

The median of three readings already handles one extreme outlier. When one channel is biased high, however, the median tends to choose the higher of the two healthy noisy readings. Averaging the agreeing healthy pair can reduce that error. The published bias experiments measured a 19.3% RMSE reduction.

Under elevated noise, this advantage does not hold: common-sample error is worse than the median and output availability falls. Reporting that trade-off is part of the engineering work.

## Understand the counterexample

If truth is 50 but readings are 58, 58 and 50, the two bad instruments agree and the healthy one may be isolated. If all read 58, no disagreement exists. Independence and the single-fault assumption are essential.

Your interview explanation can be: “I investigated when redundant calibrated measurements support a usable estimate, quantified improvement over a median baseline, and tested where the independence and single-fault assumptions break.”

Read calibration.py, validation.py, study.py and study_benchmark.py in that order. Run bias, common_mode, dual_fault and high_noise in the dashboard. Predict the outcome before reading it; explaining the counterexamples is better preparation than memorising the headline metric.
