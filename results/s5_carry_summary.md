# S5: Carry / term structure — SKIPPED, insufficient data (as pre-registered)

**Data check result**: Yahoo does expose specific dated-contract futures tickers (confirmed
reachable — e.g. `GCZ26.CMX`, `CLZ26.NYM`, `ESZ26.CME` all resolve with real OHLCV), so a near/far
carry signal is technically constructible for *recent* dates. But each individual dated contract
only carries a few years of listed trading history before expiry (e.g. `GCZ26.CMX` starts
2020-12-30, `CLZ26.NYM` starts 2017-11-21) — a genuine multi-decade carry series would require
chaining on the order of 100+ sequential contract-month tickers per market with correct roll-date
logic, which is a data-engineering effort disproportionate to this run and carries real risk of
introducing exactly the kind of splicing/look-ahead bug this run exists to catch.

A carry test restricted to the ~5-9 years where one simultaneous near/far pair happens to overlap
would fall below this run's own pre-registered **≥10-year evidence bar before a single trade was
even backtested**. Per the pre-registration ("if a clean near/far pair can't be constructed... log
SKIPPED rather than proxy it"), this is skipped cleanly. Zero tests counted toward N_TESTS.

This is a genuine data-availability gap, not a negative result — carry is one of the more
academically well-supported styles (Koijen et al.), and a paid data source with continuous
back-adjusted near/far spreads (e.g. a commercial futures database) would likely make this testable
properly in a future run.
