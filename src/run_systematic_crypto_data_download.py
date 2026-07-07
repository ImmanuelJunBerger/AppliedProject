import csv
from crypto_mlsystem.systematic_crypto_trading_lab import RAW, CLEAN, FEAT, make_market
if __name__ == '__main__':
    RAW.mkdir(parents=True, exist_ok=True); CLEAN.mkdir(parents=True, exist_ok=True); FEAT.mkdir(parents=True, exist_ok=True)
    panel = make_market()
    with (FEAT / 'full_feature_panel.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(panel[0].keys()))
        w.writeheader(); w.writerows(panel)
    (FEAT / 'full_feature_panel.parquet').write_text('Parquet placeholder; dependency unavailable in this environment. Use full_feature_panel.csv.\n')
    print(f'wrote feature panel rows={len(panel)} cols={len(panel[0])}')
