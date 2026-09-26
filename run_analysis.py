"""Run the complete retrospective study; no network required when cached."""
import argparse
from dataclasses import asdict,replace
import hashlib,json,platform
from pathlib import Path
import numpy as np
import pandas as pd
import scipy,sklearn,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter,StrMethodFormatter
from src.data import load_prices
from src.universe import DEFAULT_TICKERS,SECTOR_MAP
from src.research import Config,STRATEGIES,target_schedule,simulate,metrics,drawdowns,bootstrap_sharpe_difference

ROOT=Path(__file__).resolve().parent
COLORS=['#94a3b8','#d8aa57','#a78bfa','#22d3b0','#ff7d78','#62a8ff']

def run(refresh=False):
    cfg=Config(); out=ROOT/'outputs';out.mkdir(exist_ok=True)
    prices=load_prices(DEFAULT_TICKERS+['SPY'],cfg.start,cfg.end,ROOT/'data',refresh)
    returns=prices.pct_change(fill_method=None).iloc[1:]
    assets=returns[DEFAULT_TICKERS];test=assets.loc[cfg.test_start:]
    sensitivity=[];primary={};primary_targets={};audits=[]
    for lookback in [252,504,756]:
        c=replace(cfg,lookback=lookback)
        print(f'Building monthly targets: {lookback} sessions',flush=True)
        targets,audit=target_schedule(assets,SECTOR_MAP,c)
        audit['lookback']=lookback;audits.append(audit)
        for cost in [0,5,10,25]:
            net={};trades={}
            for name in STRATEGIES:
                net[name],_,trades[name]=simulate(test,targets[name],cost)
            spy=returns[['SPY']].loc[test.index]
            net['SPY'],_,trades['SPY']=simulate(spy,pd.DataFrame({'SPY':[1.]},index=test.index[:1]),cost)
            for name,r in net.items():
                sensitivity.append(dict(strategy=name,lookback=lookback,cost_bps=cost,**metrics(r,cfg.risk_free)))
            if lookback==cfg.lookback and cost==cfg.cost_bps:
                primary=pd.DataFrame(net);primary_targets=targets
                transactions=pd.concat(trades,names=['strategy']).reset_index(level=0)
    performance=pd.DataFrame({name:metrics(r,cfg.risk_free) for name,r in primary.items()}).T
    performance.index.name='strategy'
    perf_years=len(primary)/252
    performance['annual_traded_notional']=transactions.groupby('strategy').traded_notional.sum()/perf_years
    performance.to_csv(out/'performance_metrics.csv')
    primary.to_csv(out/'daily_net_returns.csv',index_label='Date')
    transactions.to_csv(out/'transactions.csv',index=False)
    pd.concat(audits,ignore_index=True).to_csv(out/'timing_audit.csv',index=False)
    pd.DataFrame(sensitivity).to_csv(out/'sensitivity.csv',index=False)
    all_weights=pd.concat(primary_targets,names=['strategy','return_date'])
    all_weights.to_csv(out/'monthly_weights.csv')
    latest=pd.DataFrame({name:frame.iloc[-1] for name,frame in primary_targets.items()})
    latest.to_csv(out/'latest_weights.csv',index_label='ticker')
    sector=latest.groupby(pd.Series(SECTOR_MAP)).sum()
    sector.to_csv(out/'latest_sector_weights.csv')
    years=[]
    for year,frame in primary.groupby(primary.index.year):
        for name,r in frame.items():
            years.append(dict(year=year,strategy=name,period_return=np.prod(1+r)-1,n_sessions=len(r)))
    pd.DataFrame(years).to_csv(out/'calendar_returns.csv',index=False)
    confidence=bootstrap_sharpe_difference(primary,risk_free=cfg.risk_free)
    confidence.to_csv(out/'bootstrap_sharpe_differences.csv',index_label='strategy')
    metadata=dict(config=asdict(cfg),test_first=str(primary.index[0].date()),test_last=str(primary.index[-1].date()),
        test_sessions=len(primary),rebalance_count=len(primary_targets[STRATEGIES[0]]),
        snapshot_sha256=hashlib.sha256((ROOT/'data/prices.csv').read_bytes()).hexdigest(),
        protocol_sha256=hashlib.sha256((ROOT/'protocol.json').read_bytes()).hexdigest(),
        versions=dict(python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,scipy=scipy.__version__,scikit_learn=sklearn.__version__,matplotlib=matplotlib.__version__))
    (out/'run_manifest.json').write_text(json.dumps(metadata,indent=2))
    plot_results(primary,performance,latest,confidence,pd.DataFrame(sensitivity),out)
    write_report(performance,confidence,pd.DataFrame(sensitivity),metadata,out)
    print(performance.round(4).to_string())
    return performance


def plot_results(net,performance,latest,confidence,sensitivity,out):
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,
        'axes.spines.right':False,'axes.grid':True,'grid.alpha':.15,'savefig.facecolor':'white','svg.fonttype':'none'})
    fig,axes=plt.subplots(2,1,figsize=(12,9),sharex=True,gridspec_kw={'height_ratios':[2,1]})
    for (name,r),color in zip(net.items(),COLORS):
        initial=pd.Series([1.],index=[net.index[0]-pd.offsets.BDay(1)])
        wealth=pd.concat([initial,(1+r).cumprod()])
        axes[0].plot(wealth.index,wealth*10000,label=name,color=color,lw=2)
        axes[1].plot(r.index,drawdowns(r),color=color,lw=1.5)
    axes[0].set_title('Portfolio rules tested beyond their estimation windows',loc='left',fontweight='bold',fontsize=18,pad=18)
    axes[0].set_ylabel('Growth of $10,000 (USD)');axes[0].yaxis.set_major_formatter(StrMethodFormatter('${x:,.0f}'))
    axes[0].legend(ncol=2,loc='upper left',fontsize=9)
    axes[1].set_ylabel('Drawdown');axes[1].yaxis.set_major_formatter(PercentFormatter(1))
    fig.text(.09,.01,'Retrospective study • 504-session lookback • monthly targets • 10 bps per dollar traded • fixed, hindsight-selected universe',fontsize=9,color='#475569')
    fig.tight_layout(rect=[0,.03,1,1]);fig.savefig(out/'performance.svg');fig.savefig(out/'performance.png',dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(11,8));latest.plot.barh(ax=ax,color=COLORS[:5],width=.8)
    ax.set_title('Latest monthly target allocations',loc='left',fontweight='bold');ax.xaxis.set_major_formatter(PercentFormatter(1));ax.set_xlabel('Target weight');ax.legend(fontsize=8)
    fig.tight_layout();fig.savefig(out/'allocations.svg');plt.close(fig)
    fig,ax=plt.subplots(figsize=(10,6));c=confidence.drop(index='Equal weight');y=np.arange(len(c))
    ax.hlines(y,c.lower_95,c.upper_95,color=COLORS[3],lw=3);ax.scatter(c.sharpe_difference,y,color='#0f172a',zorder=3);ax.axvline(0,color='#64748b',ls='--')
    ax.set_yticks(y,c.index);ax.set_xlabel('Sharpe difference versus equal weight');ax.set_title('Uncertainty matters: paired block-bootstrap 95% intervals',loc='left',fontweight='bold',fontsize=14)
    fig.tight_layout();fig.savefig(out/'uncertainty.svg');plt.close(fig)
    # Shareable static research card; exact data, not AI-generated artwork.
    fig=plt.figure(figsize=(12,13.5),facecolor='#0b1220');gs=fig.add_gridspec(3,1,height_ratios=[.55,1.7,1],left=.09,right=.95,top=.95,bottom=.12,hspace=.35)
    title=fig.add_subplot(gs[0]);title.axis('off');title.text(0,.85,'PORTFOLIO RESEARCH',color='#22d3b0',fontsize=14,fontweight='bold')
    title.text(0,.35,'Does optimization survive\na more realistic backtest?',color='white',fontsize=29,fontweight='bold',va='top')
    ax=fig.add_subplot(gs[1],facecolor='#0b1220')
    for name,color in [('Equal weight',COLORS[0]),('Min variance (shrinkage)',COLORS[3]),('Max Sharpe (shrinkage)',COLORS[4]),('SPY',COLORS[5])]:
        r=net[name];ax.plot(r.index,10000*(1+r).cumprod(),label=name,color=color,lw=2.8)
    ax.tick_params(colors='#cbd5e1');ax.yaxis.set_major_formatter(StrMethodFormatter('${x:,.0f}'));ax.set_title('Growth of $10,000 • after modeled trading costs',color='white',loc='left',fontsize=13,pad=16)
    ax.legend(facecolor='#0b1220',labelcolor='white',edgecolor='none',fontsize=10,loc='upper left');ax.spines['left'].set_color('#334155');ax.spines['bottom'].set_color('#334155')
    ax=fig.add_subplot(gs[2]);ax.axis('off')
    names=['Equal weight','Min variance (shrinkage)','Max Sharpe (shrinkage)','SPY']
    cells=[[n,f'{performance.loc[n,"cagr"]:.1%}',f'{performance.loc[n,"sharpe"]:.2f}',f'{performance.loc[n,"max_drawdown"]:.1%}'] for n in names]
    table=ax.table(cellText=cells,colLabels=['Portfolio','CAGR','Sharpe','Max drawdown'],colWidths=[.49,.16,.15,.20],bbox=[0,.02,1,.88])
    table.auto_set_font_size(False);table.set_fontsize(12)
    for (row,col),cell in table.get_celld().items():
        cell.set_facecolor('#122033' if row==0 else '#0b1220');cell.set_edgecolor('#334155');cell.set_text_props(color='#22d3b0' if row==0 else 'white',ha='left' if col==0 else 'center')
    fig.text(.09,.075,f'{net.index[0]:%b %d, %Y} – {net.index[-1]:%b %d, %Y} | Monthly rebalancing | 10 bps per dollar traded',color='#cbd5e1',fontsize=11)
    fig.text(.09,.044,'Retrospective, hindsight-selected universe. Hypothetical performance, not live returns.\n20 U.S. equities • 15% stock cap / 35% sector cap at rebalance • AI-assisted Python study',color='#94a3b8',fontsize=10,linespacing=1.6)
    fig.savefig(out/'linkedin_research_card.png',dpi=120,facecolor=fig.get_facecolor());plt.close(fig)


def write_report(perf,ci,sens,meta,out):
    lines=['# Research results','',f"Test: **{meta['test_first']} to {meta['test_last']}**, {meta['test_sessions']} sessions, {meta['rebalance_count']} monthly allocations.",'',
      'All figures are hypothetical, net of modeled transaction costs. Primary specification: 504 prior sessions, 10 bps per dollar traded, 4% constant annual risk-free assumption.','',
      '| Strategy | CAGR | Volatility | Sharpe | Sortino | Max drawdown | Annual traded notional |','|---|---:|---:|---:|---:|---:|---:|']
    for name,r in perf.iterrows():
        lines.append(f'| {name} | {r.cagr:.2%} | {r.volatility:.2%} | {r.sharpe:.2f} | {r.sortino:.2f} | {r.max_drawdown:.2%} | {r.annual_traded_notional:.2f}× |')
    lines+=['','## Interpretation','',
      'The minimum-variance rule targets risk, not maximum return. A lower CAGR is not by itself a failure of that objective. Maximum-Sharpe targets depend on noisy historical mean estimates; shrinkage here applies to covariance only.','',
      '## Is the Sharpe difference convincing?','',
      'Paired circular moving-block bootstrap: 1,000 replications, 21-session blocks, seed 7. Differences are relative to equal weight; intervals are descriptive and not adjusted for multiple comparisons. The bootstrap resamples realized strategy returns; it does not re-fit the optimizer or remove universe-selection bias.','',
      '| Strategy | Sharpe difference | 95% interval |','|---|---:|---:|']
    for name,r in ci.iterrows():
        lines.append(f'| {name} | {r.sharpe_difference:.2f} | [{r.lower_95:.2f}, {r.upper_95:.2f}] |')
    lines+=['','## Sensitivity (all alternatives reported)','',
      'Lookbacks: 252, 504, 756 sessions. Costs: 0, 5, 10, 25 bps per dollar traded. Each lookback recomputes the targets; costs do not retune the strategy.','',
      '| Strategy | CAGR range across 12 specifications | Sharpe range |','|---|---:|---:|']
    for name,g in sens.groupby('strategy',sort=False):
        lines.append(f'| {name} | {g.cagr.min():.2%} to {g.cagr.max():.2%} | {g.sharpe.min():.2f} to {g.sharpe.max():.2f} |')
    lines+=['','## Limits on the conclusion','',
      '- The 20-stock universe was selected with hindsight and contains surviving firms. This is not a point-in-time investable-universe test.',
      '- This was designed retrospectively; dates unseen by each optimizer are not an untouched research holdout.',
      '- Adjusted-close data can be revised. Current sector classifications are fixed through history.',
      '- Execution at adjusted closing prices is idealized; fixed trading costs do not model liquidity, impact or variable spreads.',
      '- Stock and sector caps apply at rebalances; weights drift between them.',
      '- Taxes, CAD/USD exposure, financing, actual short-term rate history and final liquidation costs are omitted.',
      '- All portfolios include their initial entry fee. SPY is buy-and-hold; the five stock rules rebalance monthly.',
      '- No strategy is claimed to have demonstrated persistent alpha or statistically established superiority.','']
    (out/'RESULTS.md').write_text('\n'.join(lines))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--refresh',action='store_true')
    run(parser.parse_args().refresh)
