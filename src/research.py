"""Portfolio targets, self-financing trades, and lagged walk-forward simulation."""
from dataclasses import dataclass
import numpy as np
import pandas as pd
from scipy.optimize import minimize, brentq
from sklearn.covariance import LedoitWolf

DAYS = 252
STRATEGIES = ['Equal weight', 'Inverse volatility', 'Min variance (sample)', 'Min variance (shrinkage)', 'Max Sharpe (shrinkage)']

@dataclass(frozen=True)
class Config:
    start: str = '2020-01-01'
    end: str = '2026-09-26'
    test_start: str = '2024-01-01'
    lookback: int = 504
    cost_bps: float = 10.0
    risk_free: float = 0.04
    stock_cap: float = 0.15
    sector_cap: float = 0.35


def sector_matrix(tickers, sectors):
    names = sorted({sectors[t] for t in tickers})
    return np.array([[float(sectors[t] == name) for t in tickers] for name in names])


def validate_weights(w, sectors, cfg, tol=1e-6):
    a = sector_matrix(list(w.index), sectors)
    if not np.isfinite(w).all() or abs(w.sum()-1) > tol or w.min() < -tol or w.max() > cfg.stock_cap+tol or (a@w.to_numpy()).max() > cfg.sector_cap+tol:
        raise ValueError('Target weights violate investment constraints.')


def target_weights(train, strategy, sectors, cfg):
    x = train.to_numpy()
    tickers = list(train.columns)
    a = sector_matrix(tickers, sectors)
    n = len(tickers)
    if n*cfg.stock_cap < 1-1e-9:
        raise ValueError('Infeasible stock cap.')
    sample = np.cov(x, rowvar=False)*DAYS
    if strategy == 'Equal weight':
        w = pd.Series(1/n, index=tickers)
        validate_weights(w,sectors,cfg)
        return w
    cov = LedoitWolf().fit(x).covariance_*DAYS if 'shrinkage' in strategy else sample
    mu = x.mean(axis=0)*DAYS
    inv = 1/np.sqrt(np.diag(sample))
    inv /= inv.sum()
    if strategy == 'Inverse volatility':
        # Nearest feasible allocation if raw inverse-volatility breaches caps.
        objective = lambda w: float(np.sum((w-inv)**2))
    elif strategy.startswith('Min variance'):
        objective = lambda w: float(w@cov@w)
    elif strategy == 'Max Sharpe (shrinkage)':
        objective = lambda w: -float((w@mu-cfg.risk_free)/np.sqrt(w@cov@w))
    else:
        raise ValueError(f'Unknown strategy: {strategy}')
    constraints=[{'type':'eq','fun':lambda w: w.sum()-1},
                 {'type':'ineq','fun':lambda w: cfg.sector_cap-a@w}]
    starts=[np.repeat(1/n,n)]
    if strategy.startswith('Max Sharpe'):
        starts.append(inv)
    solutions=[]
    for start in starts:
        result=minimize(objective,start,method='SLSQP',bounds=[(0,cfg.stock_cap)]*n,
                        constraints=constraints,options={'maxiter':1500,'ftol':1e-11})
        if result.success:
            w=pd.Series(result.x,index=tickers)
            validate_weights(w,sectors,cfg)
            solutions.append((objective(w.to_numpy()),w))
    if not solutions:
        raise RuntimeError(f'Optimizer failed for {strategy}; no silent fallback.')
    return min(solutions,key=lambda p:p[0])[1]


def target_schedule(returns, sectors, cfg):
    test=returns.loc[cfg.test_start:]
    months=test.index.to_period('M')
    dates=test.index[~months.duplicated()]
    targets={name:{} for name in STRATEGIES}
    audit=[]
    for date in dates:
        i=returns.index.get_loc(date)
        # Return i is earned after execution at close i-1. Train through i-2.
        train=returns.iloc[i-cfg.lookback-1:i-1]
        if len(train)!=cfg.lookback or i-cfg.lookback-1 < 0:
            raise ValueError('Not enough pre-test observations for the requested lookback.')
        for name in STRATEGIES:
            targets[name][date]=target_weights(train,name,sectors,cfg)
        audit.append(dict(return_date=date,execution_date=returns.index[i-1],
                          training_start=train.index[0],training_end=train.index[-1],n_obs=len(train)))
    return {name:pd.DataFrame(weights).T for name,weights in targets.items()},pd.DataFrame(audit)


def transaction_fraction(pre, target, rate):
    """Exact fee fraction f = rate * sum(abs((1-f)*target - pre)).

    pre/target are risky weights; zero pre means an initial cash-funded purchase.
    Sum of buys plus sells is traded notional; this is NOT half-turnover.
    """
    if not 0 <= rate < .1:
        raise ValueError('Cost rate outside supported range.')
    if rate == 0:
        return 0.0
    return brentq(lambda f: f-rate*np.abs((1-f)*target-pre).sum(),0,2*rate,xtol=1e-14)


def simulate(returns, targets, cost_bps):
    pre=np.zeros(returns.shape[1])
    net,gross,rows=[],[],[]
    for date,row in returns.iterrows():
        fee=0.0
        if date in targets.index:
            target=targets.loc[date,returns.columns].to_numpy(dtype=float)
            fee=transaction_fraction(pre,target,cost_bps/10000)
            notional=float(np.abs((1-fee)*target-pre).sum())
            rows.append(dict(date=date,traded_notional=notional,cost_fraction=fee))
            pre=target
        elif pre.sum() == 0:
            raise ValueError('Missing initial allocation.')
        r=row.to_numpy()
        g=float(pre@r)
        gross.append(g)
        net.append((1-fee)*(1+g)-1)
        pre=pre*(1+r)/(1+g)  # drift until next scheduled trade
    return pd.Series(net,index=returns.index),pd.Series(gross,index=returns.index),pd.DataFrame(rows)


def drawdowns(r):
    wealth=(1+r).cumprod()
    return wealth/wealth.cummax().clip(lower=1)-1


def metrics(r, risk_free=.04):
    x=np.asarray(r,dtype=float)
    if len(x)<2 or not np.isfinite(x).all() or (x<=-1).any():
        raise ValueError('Invalid return series.')
    rf=(1+risk_free)**(1/DAYS)-1
    excess=x-rf
    vol=np.std(x,ddof=1)*np.sqrt(DAYS)
    downside=np.sqrt(np.mean(np.minimum(excess,0)**2))*np.sqrt(DAYS)
    total=float(np.prod(1+x)-1)
    cagr=(1+total)**(DAYS/len(x))-1
    dd=float(drawdowns(pd.Series(x)).min())
    return dict(total_return=total,cagr=cagr,volatility=vol,
                sharpe=float(excess.mean()*DAYS/vol) if vol>1e-12 else np.nan,
                sortino=float(excess.mean()*DAYS/downside) if downside>1e-12 else np.nan,
                max_drawdown=dd,calmar=cagr/abs(dd) if dd<0 else np.nan)


def bootstrap_sharpe_difference(returns, benchmark='Equal weight', repetitions=1000, block=21, seed=7, risk_free=.04):
    """Paired circular moving-block bootstrap; descriptive uncertainty, not a forecast."""
    rng=np.random.default_rng(seed)
    x=returns.to_numpy()
    n,k=x.shape
    base=list(returns.columns).index(benchmark)
    rf=(1+risk_free)**(1/DAYS)-1
    diffs=np.empty((repetitions,k))
    for b in range(repetitions):
        starts=rng.integers(0,n,size=int(np.ceil(n/block)))
        indices=((starts[:,None]+np.arange(block))%n).ravel()[:n]
        sample=x[indices]
        ratios=(sample.mean(axis=0)-rf)/sample.std(axis=0,ddof=1)*np.sqrt(DAYS)
        diffs[b]=ratios-ratios[base]
    point=(x.mean(axis=0)-rf)/x.std(axis=0,ddof=1)*np.sqrt(DAYS)
    return pd.DataFrame(dict(sharpe_difference=point-point[base],
        lower_95=np.quantile(diffs,.025,axis=0),upper_95=np.quantile(diffs,.975,axis=0)),index=returns.columns)
