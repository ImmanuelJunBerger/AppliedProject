# S3: Pre-FOMC announcement drift — summary

255 scheduled FOMC meetings matched to `^GSPC` close(t-1)->close(t) returns, 1994-2026 (t = the
Fed's own historical-archive statement/announcement day; ad-hoc unscheduled "Conference Call"
events excluded — see `src/data_tradfi.py` parser notes).

| Slice | Net Sharpe (ann., 8 events/yr) | Mean return/event | Win rate | p-value | n |
|---|---|---|---|---|---|
| Full sample | 0.55 | +0.227% | 53.7% | **0.00095** | 255 |
| Ex 2008-2009 crisis | 0.41 | +0.154% | 52.3% | 0.013 | 239 |
| Ex 2020 COVID | 0.52 | +0.213% | 53.6% | 0.0019 | 248 |
| **In-sample (1994-2016)** | **0.75** | +0.311% | 58.4% | **0.00021** | 178 |
| **Holdout (2016-2026)** | **0.078** | +0.031% | 42.9% | **0.40** | 77 |

Full detail: `results/s3_fomc_raw.json`. Event-level data: `results/s3_fomc_events.csv`.

**Real historically, but decaying — does not clear this run's own evidence bar.** The full-sample
effect is robust (survives excluding both the 2008-2009 crisis and 2020 COVID, p<0.02 in both
cuts), matching the well-documented Lucca-Moench pre-FOMC drift finding. But split at the 70/30
holdout boundary (2016), the effect is strong and significant in-sample (Sharpe 0.75, p=0.0002) and
statistically indistinguishable from zero in holdout (Sharpe 0.08, p=0.40, win rate actually below
50%). This is consistent with a documented, plausible story: an effect that gets publicized and
traded away is exactly what efficient-markets logic predicts, and pre-FOMC drift has been widely
discussed in practitioner and academic literature since well before 2016.

**Verdict: does not pass — positive holdout is a hard requirement in this run's pre-registered
evidence bar, and this fails it.** Excluded from the portfolio-construction candidate set on that
basis, despite the attractive full-sample number. This is exactly the discipline the run exists to
enforce: a strategy that looks good until you actually check the part of history it hasn't seen yet.
