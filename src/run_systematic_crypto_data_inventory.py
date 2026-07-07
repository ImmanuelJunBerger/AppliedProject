import csv
from crypto_mlsystem.systematic_crypto_trading_lab import api_inventory, LAB
if __name__ == '__main__':
    LAB.mkdir(parents=True, exist_ok=True)
    inv = api_inventory()
    with (LAB / 'api_data_inventory.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(inv[0].keys()))
        w.writeheader(); w.writerows(inv)
    (LAB / 'api_data_inventory.md').write_text('| source | status | reason |\n|---|---|---|\n' + '\n'.join(f"| {r['source_name']} | {r['status']} | {r['reason']} |" for r in inv))
    print(f'wrote {len(inv)} inventory rows')
