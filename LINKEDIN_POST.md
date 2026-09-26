# LinkedIn post draft

Does a more sophisticated portfolio actually produce better results?

I explored that question in an AI-assisted Python research project comparing five portfolio construction rules with SPY across 20 U.S. equities.

I extended the analysis beyond a static optimization: monthly walk-forward testing, realistic weight drift, transaction costs, stock and sector limits, and Ledoit–Wolf covariance shrinkage. I also tested different estimation windows and trading costs, and used block bootstrapping to examine uncertainty.

The most interesting result: the portfolio optimized for Sharpe ratio did not achieve the highest realized Sharpe ratio.

From January 2, 2024 to September 25, 2026, after modeled trading costs:

• Maximum Sharpe: 27.4% annualized return, 1.41 Sharpe.
• Equal weight: 24.7% annualized return, 1.49 Sharpe.
• Minimum variance with shrinkage: 17.2% annualized return, with a 10.2% maximum drawdown versus 18.8% for SPY.

My takeaway: higher returns, lower risk and stronger risk-adjusted performance are different objectives. A more complex optimizer does not automatically improve all three.

These are hypothetical, retrospective results—not live returns. The stock universe was selected with hindsight, and the uncertainty intervals do not establish that the optimized rules outperform equal weighting.

The project includes the Python code, notebook, data snapshot, methodology, results and 11 automated tests. I used OpenAI Codex to help develop and test the implementation.

Project on GitHub: https://github.com/paytonadelaar-dot/portfolio-research

For those working in portfolio research: what would you challenge first—the return estimates, the universe selection, or the execution assumptions?

#PortfolioManagement #QuantitativeFinance #Python #InvestmentResearch
