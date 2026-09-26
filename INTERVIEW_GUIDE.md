# Be ready to explain the project

## A 30-second description

“I developed an AI-assisted Python study comparing portfolio construction rules with equal weight and SPY. It refits monthly using only lagged historical inputs, lets holdings drift between trades, and deducts trading costs. The max-Sharpe portfolio had the highest return in the main test, but equal weight had the higher realized Sharpe ratio. The main lesson is that optimizing a historical objective does not guarantee the best future risk-adjusted result.”

Use this description only when you can explain the mechanics below; do not claim you manually wrote every line.

## Why can a maximum-Sharpe strategy lose on Sharpe?

It maximizes an **estimated historical** Sharpe, not the unknowable future Sharpe. Expected returns are noisy, correlations change, and frequent turnover costs money. In this test its CAGR was 27.39%, versus 24.69% for equal weight, but its volatility was also higher: 15.26% versus 12.73%. Realized Sharpe was 1.41 versus 1.49.

## What does shrinkage do?

It blends sample covariance with a simpler scaled-identity estimate, with the blend estimated by Ledoit–Wolf. It can make covariance estimation more stable. It does not repair biased stock selection or automatically improve expected-return estimates.

## Why do weights drift?

If one stock rises while another is flat, the winner becomes a larger fraction of the portfolio. Applying the same weights to every day's returns would implicitly rebalance every day. This model trades monthly and updates weights between trades.

## What does 10 bps mean?

Ten basis points is 0.10% of each dollar traded. Both purchases and sales count. A 10% sale plus a 10% purchase means approximately 20% traded notional and a cost near 0.02% of portfolio value. The engine solves the fee-financing equation exactly rather than borrowing the fee.

## What prevents look-ahead?

Each target uses returns ending at t−2, executes at t−1 close, and first earns the return dated t. A test changes execution-day and future returns and verifies that the first target remains unchanged. This prevents a particular timing error; it does not remove hindsight in the research design.

## What does the uncertainty interval say?

The max-Sharpe minus equal-weight Sharpe difference was −0.08, and its descriptive 95% interval spans zero. That is not strong evidence that either strategy is better. The interval is conditional on this history and selected universe and is not adjusted for multiple comparisons.

## What is the biggest weakness?

The 20 stocks were selected today, with hindsight and survivorship bias. A stronger next study would use a point-in-time universe with delisted securities or a predefined diversified ETF universe, then freeze the research design and collect genuinely new observations.

## Why not present only the best specification?

Selecting the best lookback or cost assumption after observing performance creates another opportunity to overfit. This report retains 504 sessions and 10 bps as its primary case and shows every sensitivity result.

## What was actually tested?

Eleven automated tests cover future-data isolation, covariance ordering, target constraints, missing-price rejection, infeasible constraints, weight drift, exact initial/rebalance fees, the first-day drawdown, Sortino downside deviation and the direction of cost impact. The supplied notebook cells and complete pipeline were also run successfully.
