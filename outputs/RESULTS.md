# Research results

Test: **2024-01-02 to 2026-09-25**, 686 sessions, 33 monthly allocations.

All figures are hypothetical, net of modeled transaction costs. Primary specification: 504 prior sessions, 10 bps per dollar traded, 4% constant annual risk-free assumption.

| Strategy | CAGR | Volatility | Sharpe | Sortino | Max drawdown | Annual traded notional |
|---|---:|---:|---:|---:|---:|---:|
| Equal weight | 24.69% | 12.73% | 1.49 | 2.23 | -16.20% | 1.01× |
| Inverse volatility | 21.82% | 11.43% | 1.44 | 2.15 | -14.51% | 0.98× |
| Min variance (sample) | 17.04% | 10.54% | 1.17 | 1.74 | -9.99% | 1.55× |
| Min variance (shrinkage) | 17.15% | 10.51% | 1.19 | 1.76 | -10.16% | 1.51× |
| Max Sharpe (shrinkage) | 27.39% | 15.26% | 1.41 | 2.13 | -18.39% | 3.73× |
| SPY | 20.84% | 15.58% | 1.04 | 1.54 | -18.76% | 0.37× |

## Interpretation

The minimum-variance rule targets risk, not maximum return. A lower CAGR is not by itself a failure of that objective. Maximum-Sharpe targets depend on noisy historical mean estimates; shrinkage here applies to covariance only.

## Is the Sharpe difference convincing?

Paired circular moving-block bootstrap: 1,000 replications, 21-session blocks, seed 7. Differences are relative to equal weight; intervals are descriptive and not adjusted for multiple comparisons. The bootstrap resamples realized strategy returns; it does not re-fit the optimizer or remove universe-selection bias.

| Strategy | Sharpe difference | 95% interval |
|---|---:|---:|
| Equal weight | 0.00 | [0.00, 0.00] |
| Inverse volatility | -0.05 | [-0.29, 0.20] |
| Min variance (sample) | -0.32 | [-1.25, 0.59] |
| Min variance (shrinkage) | -0.30 | [-1.23, 0.58] |
| Max Sharpe (shrinkage) | -0.08 | [-0.86, 0.50] |
| SPY | -0.45 | [-0.98, -0.05] |

## Sensitivity (all alternatives reported)

Lookbacks: 252, 504, 756 sessions. Costs: 0, 5, 10, 25 bps per dollar traded. Each lookback recomputes the targets; costs do not retune the strategy.

| Strategy | CAGR range across 12 specifications | Sharpe range |
|---|---:|---:|
| Equal weight | 24.50% to 24.82% | 1.48 to 1.50 |
| Inverse volatility | 21.42% to 21.94% | 1.40 to 1.45 |
| Min variance (sample) | 16.10% to 18.28% | 1.09 to 1.31 |
| Min variance (shrinkage) | 16.26% to 18.25% | 1.11 to 1.32 |
| Max Sharpe (shrinkage) | 24.30% to 28.97% | 1.26 to 1.54 |
| SPY | 20.78% to 20.89% | 1.04 to 1.04 |

## Limits on the conclusion

- The 20-stock universe was selected with hindsight and contains surviving firms. This is not a point-in-time investable-universe test.
- This was designed retrospectively; dates unseen by each optimizer are not an untouched research holdout.
- Adjusted-close data can be revised. Current sector classifications are fixed through history.
- Execution at adjusted closing prices is idealized; fixed trading costs do not model liquidity, impact or variable spreads.
- Stock and sector caps apply at rebalances; weights drift between them.
- Taxes, CAD/USD exposure, financing, actual short-term rate history and final liquidation costs are omitted.
- All portfolios include their initial entry fee. SPY is buy-and-hold; the five stock rules rebalance monthly.
- No strategy is claimed to have demonstrated persistent alpha or statistically established superiority.
