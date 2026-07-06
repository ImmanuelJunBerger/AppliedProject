# New data classification audit

This audit corrects the distinction between statistical Tier-1 evidence and genuinely new alternative data.

The frozen strategy **btc_eth_macro_gate_balanced** was not modified, reselected, or retuned. No strategy was run.

## Corrected Tier-1 grouping

- Original Tier-1 count: 2
- Original Tier-1 features: funding_change, credit_spread_level
- Genuine New / Alternative Data Tier-1 count: 1
- Genuine New / Alternative Data Tier-1 features: funding_change
- Additional Macro / WRDS Extension Tier-1 count: 1
- Additional Macro / WRDS Extension Tier-1 features: credit_spread_level
- Existing Control / Redundancy Tier-1 count: 0
- Existing Control / Redundancy Tier-1 features: None

## Features moved between categories

| Feature | From | To | Reason |
|---|---|---|---|
| credit_spread_level | New Data Tier-1 gate count | Additional Macro / WRDS Extension Tier-1 | WRDS/macro variable; useful as a macro extension but not genuinely new alternative data beyond the macro-regime project. |

## Corrected strategy gate

The strategy-testing gate is computed using only Genuine New / Alternative Data Tier-1 features.

- Required genuine new-data Tier-1 features: 3
- Available genuine new-data Tier-1 features: 1
- Strategy gate passes: No
- Strategy ran: No

## Final conclusion

Yes, **funding_change** is the only genuine new-data Tier-1 feature in the current run. **credit_spread_level** is better described as an additional macro / WRDS extension, not as a genuinely new alternative-data trigger. The 3-feature genuine-new-data gate does not pass. No new-data strategy should be run; keep **btc_eth_macro_gate_balanced** unchanged.
