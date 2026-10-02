"""Reproduce numeric outputs; add --figure to render the sensitivity table."""
import argparse
import csv
import json
from dataclasses import asdict, replace
from pathlib import Path
from model import Scenario

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--figure', action='store_true')
    args = parser.parse_args()
    out = ROOT / 'outputs'
    out.mkdir(exist_ok=True)
    base = Scenario()
    prices = (75, 100, 125, 150, 175, 200)
    rates = (.08, .10, .12, .14, .16)
    rows = [[p, *(replace(base, purchase_price=p, discount_rate=r).required_fcf() for r in rates)] for p in prices]
    with (out / 'sensitivity.csv').open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['hypothetical_price_usd_m', *(f'required_fcf_at_{r:.0%}_usd_m' for r in rates)])
        writer.writerows(rows)
    variants = {'illustrative_base':base,
                'one_year_delay_fixed_year_5_end':replace(base, ramp=(0, *base.ramp[:-1])),
                'one_year_delay_shifted_year_6_end':replace(base, ramp=(0, *base.ramp)),
                'seven_year_benefit_horizon':replace(base, ramp=(*base.ramp, 1, 1))}
    results = {k:{'assumptions':asdict(s), 'required_annual_run_rate_fcf_usd_m':s.required_fcf(),
                  'npv_usd_m':s.npv(s.required_fcf())} for k,s in variants.items()}
    (out / 'results.json').write_text(json.dumps(results, indent=2)+'\n')
    with (out / 'base_cash_flows.csv').open('w', newline='') as f:
        writer=csv.writer(f)
        writer.writerow(['year_after_close','net_cash_flow_usd_m','discount_factor','pv_usd_m'])
        for t,cf in enumerate(base.cash_flows(base.required_fcf())):
            factor=(1+base.discount_rate)**-t
            writer.writerow([t,cf,factor,cf*factor])
    print(json.dumps({k:round(v['required_annual_run_rate_fcf_usd_m'],2) for k,v in results.items()}, indent=2))
    if args.figure:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        plt.rcParams['text.parse_math'] = False
        fig, ax = plt.subplots(figsize=(12, 8), dpi=180)
        fig.patch.set_facecolor('#f6f7f9')
        ax.axis('off')
        fig.text(.065,.92,'NEBIUS / INFERIZE', fontsize=13, color='#52647a', weight='bold')
        fig.text(.065,.862,'What cash flow would justify the deal?', fontsize=24, weight='bold', color='#132c43')
        fig.text(.065,.812,'Required annual run-rate incremental FCF · USD millions · after tax, unlevered', fontsize=12, color='#52647a')
        table=ax.table(cellText=[[f'${row[0]:.0f}m', *(f'${v:.1f}m' for v in row[1:])] for row in rows],
                       colLabels=['Assumed price', *(f'{r:.0%} discount rate' for r in rates)],
                       cellLoc='center',bbox=[0,.26,1,.57])
        table.auto_set_font_size(False)
        table.set_fontsize(12)
        for (i,j), cell in table.get_celld().items():
            cell.set_edgecolor('white')
            cell.set_linewidth(2)
            cell.set_facecolor('#132c43' if i==0 else ('#e4ebf1' if i%2 else '#ffffff'))
            cell.get_text().set_color('white' if i==0 else '#132c43')
            if i==0: cell.get_text().set_fontsize(10)
        table[(3,3)].set_facecolor('#147d78')
        table[(3,3)].get_text().set_color('white')
        table[(3,3)].get_text().set_weight('bold')
        fig.text(.065,.255,'Base scenario: $125m price + $10m integration; 12% discount rate.', fontsize=12, weight='bold', color='#132c43')
        fig.text(.065,.207,'All scenarios: upfront integration $10m; year-end FCF ramps 25% / 60% / 100% / 100% / 100%.\nFive years from close; no terminal value. Figures are break-even requirements, not forecasts.', fontsize=10.5, linespacing=1.6, color='#52647a')
        fig.text(.065,.11,'Transaction terms undisclosed. CTech estimated $100–150m (Oct 1, 2026); other prices are stress cases.\nSources: Nebius announcement and CTech. Model assumptions and calculations: Payton Adelaar.', fontsize=9.5, linespacing=1.6, color='#52647a')
        plt.subplots_adjust(left=.065,right=.965,top=.86,bottom=.13)
        fig.savefig(out/'sensitivity.png', facecolor=fig.get_facecolor())
        plt.close(fig)


if __name__ == '__main__':
    main()
