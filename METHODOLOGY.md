# Methodology and model audit

## Universe and scope

Twenty U.S. equities plus SPY, inherited from the original project. The universe is fixed, hindsight-selected and survivorship-biased. It is **not** a historical S&P 500 membership reconstruction. Sector labels are static. SPY is an ETF benchmark, not the S&P 500 total-return index. All calculations are in USD.

Data: Yahoo Finance daily adjusted closes, January 2020 through September 25, 2026. Adjusted close accounts for corporate actions as provided by the source. No price history is invented, forward-filled or silently discarded. `data/provenance.json` records retrieval time, dates and SHA-256. The cached snapshot supports an offline rerun; `--refresh` deliberately replaces it. Market data is third-party material, not original code.

## The five stock rules

| Rule | Inputs and objective |
|---|---|
| Equal weight | 5% per stock; reset monthly |
| Inverse volatility | Inverse sample volatility; squared-distance projection onto feasible weights if necessary |
| Min variance (sample) | Minimize wᵀΣw using sample covariance |
| Min variance (shrinkage) | Minimize wᵀΣw using Ledoit–Wolf covariance |
| Max Sharpe (shrinkage) | Maximize (wᵀμ − 4%)/sqrt(wᵀΣw), using arithmetic historical mean returns and Ledoit–Wolf covariance |

All target stock portfolios are long-only and fully invested, with a 15% name cap and 35% sector cap. Constraints apply to **target weights**, not every day's drifted weights. SLSQP is used for constrained numerical optimization. Max-Sharpe uses two starting points and retains the better successful feasible solution; this does not prove global optimality. Failed optimization aborts rather than quietly substituting another strategy.

Ledoit–Wolf shrinks covariance toward a scaled identity matrix. It does **not** make historical expected returns reliable. No return shrinkage, Black–Litterman or factor model is implemented.

## The timing convention

For the first trading session of each month, indexed t:

1. Estimate targets from 504 daily return observations ending at close t−2.
2. Execute at close t−1, with a full session between the final estimation input and execution.
3. Earn the close t−1 to close t return using those targets.
4. Drift risky weights with asset returns until the next monthly rebalance.

`timing_audit.csv` records training start/end, execution date and first return date for every lookback and rebalance. The first allocation is executed before the first reported test return; its fee is charged to that first return. Later test observations can enter later estimation windows, which is how walk-forward operation works. No future observation enters a given target.

This is an idealized close-execution backtest, not an order-fill simulator. Fractional shares and reinvested dividends are assumed. The risk-free rate is an exogenous, constant 4% assumption, not a historical Treasury series.

## Trading costs and self-financing portfolios

Let p be risky weights just before a trade, w the new target weights, c the fee rate per dollar traded, and f the fee as a fraction of pre-trade equity. Solve:

`f = c × sum(abs((1−f) × w − p))`

The initial state is cash, represented by p = 0. The initial fee is consequently c/(1+c). Buys and sells both incur costs. Reported traded notional is their sum, **not half-turnover**. There is no borrowing to pay fees.

The day's net portfolio return is `(1−f) × (1+w·r) − 1`. End-of-day risky weights are `w_i × (1+r_i)/(1+w·r)`. Between trades, f = 0. Costs are modeled at 10 bps in the primary run, with 0/5/10/25 bps sensitivity. No terminal liquidation is modeled. SPY incurs its initial entry fee and then remains buy-and-hold.

## Metrics

- Total return: product of (1 + daily net return) minus 1.
- CAGR: compound growth annualized with 252 sessions per year.
- Volatility: sample daily standard deviation × sqrt(252).
- Sharpe: mean daily excess return / sample daily standard deviation × sqrt(252). Daily risk-free = 1.04^(1/252) − 1.
- Sortino: annualized mean daily excess return divided by annualized root-mean-square negative daily excess return. The denominator includes **all** sessions, with zero for nonnegative excess observations.
- Drawdown: wealth relative to its running peak, including initial wealth = 1. This correctly captures a loss on the first session.
- Calmar: CAGR / absolute maximum drawdown.
- Annual traded notional: sum of traded notional / (test sessions / 252), including initial entry.

## Robustness and uncertainty

Three lookbacks (252/504/756) × four cost assumptions are reported. The 504-session, 10-bps case remains the primary specification regardless of which combination looks best.

The paired circular moving-block bootstrap resamples all strategy-return columns together in 21-session blocks. We use 1,000 draws with seed 7 and report percentile intervals for Sharpe differences versus equal weight. This retains some short-horizon dependence but assumes the sampled history is informative; it does not replicate the full estimation-and-trading process, capture selection bias, account for multiple comparisons, or establish future performance.

## Corrections relative to version 1

- Replaced constant-weight daily return multiplication with explicit monthly trading and weight drift.
- Added exact fee financing, including the initial allocation.
- Included initial capital in the drawdown peak calculation.
- Replaced negative-return-only standard deviation with downside root-mean-square deviation.
- Eliminated implicit covariance/weight ordering risk by constructing both from the same ordered columns; added a permutation test.
- Replaced open-ended dates and permissive caching with a fixed window, request metadata and data hash.
- Removed the claim that a manually selected present-day stock universe avoids data-mining.
- Replaced the old notebook and runner so there is one consistent research engine.

## Sources

- [LedoitWolf estimator, scikit-learn](https://scikit-learn.org/stable/modules/generated/sklearn.covariance.LedoitWolf.html)
- [Ledoit and Wolf (2004), A Well-Conditioned Estimator for Large-Dimensional Covariance Matrices](https://doi.org/10.1016/S0047-259X(03)00096-4)
- [Sortino ratio implementation, PerformanceAnalytics](https://github.com/R-Finance/PerformanceAnalytics/blob/master/R/SortinoRatio.R)
- [Yahoo Finance](https://finance.yahoo.com/) — adjusted-close price source

Educational research, not personalized investment advice. The results are hypothetical and do not establish persistent alpha.
