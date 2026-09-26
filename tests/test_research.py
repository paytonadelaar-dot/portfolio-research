import unittest
from dataclasses import replace
import numpy as np
import pandas as pd
from src.data import validate_prices
from src.research import Config, STRATEGIES, drawdowns, metrics, simulate, target_weights, target_schedule, transaction_fraction, validate_weights
from src.universe import DEFAULT_TICKERS,SECTOR_MAP

class ResearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng=np.random.default_rng(11)
        cls.returns=pd.DataFrame(rng.normal(.0003,.01,(600,20)),
            index=pd.bdate_range('2022-01-03',periods=600),columns=DEFAULT_TICKERS)

    def test_initial_loss_is_drawdown(self):
        np.testing.assert_allclose(drawdowns(pd.Series([-.1,0,.2])),[-.1,-.1,0])

    def test_holdings_drift_without_daily_rebalancing(self):
        dates=pd.date_range('2024-01-01',periods=2)
        r=pd.DataFrame([[1,0],[0,1]],index=dates,columns=['A','B'])
        t=pd.DataFrame([[.5,.5]],index=dates[:1],columns=r.columns)
        net,_,_=simulate(r,t,0)
        self.assertAlmostEqual(np.prod(1+net),2)
        self.assertAlmostEqual(net.iloc[1],1/3)

    def test_exact_initial_cost(self):
        fee=transaction_fraction(np.zeros(2),np.array([.5,.5]),.001)
        self.assertAlmostEqual(fee,.001/1.001,places=12)

    def test_rebalance_fee_is_self_financing(self):
        pre=np.array([.8,.2]); target=np.array([.3,.7]);rate=.0025
        fee=transaction_fraction(pre,target,rate)
        self.assertAlmostEqual(fee,rate*np.abs((1-fee)*target-pre).sum(),places=12)

    def test_sortino_uses_all_observations(self):
        r=pd.Series([-.1,.1,0,0])
        m=metrics(r,risk_free=.02)
        rf=1.02**(1/252)-1
        downside=np.sqrt(np.mean(np.minimum(r-rf,0)**2))*np.sqrt(252)
        self.assertAlmostEqual(m['sortino'],(r-rf).mean()*252/downside)

    def test_all_rules_respect_caps(self):
        for name in STRATEGIES:
            w=target_weights(self.returns.iloc[:252],name,SECTOR_MAP,Config())
            validate_weights(w,SECTOR_MAP,Config())

    def test_covariance_alignment_is_order_invariant(self):
        train=self.returns.iloc[:252]
        w=target_weights(train,'Min variance (shrinkage)',SECTOR_MAP,Config())
        z=target_weights(train[train.columns[::-1]],'Min variance (shrinkage)',SECTOR_MAP,Config())
        np.testing.assert_allclose(w,z.reindex(w.index),atol=1e-6)

    def test_future_and_execution_day_do_not_change_first_target(self):
        r=self.returns.iloc[:280].copy()
        date=r.index[260]
        cfg=replace(Config(),test_start=str(date.date()),lookback=252)
        a,audit=target_schedule(r,SECTOR_MAP,cfg)
        r.iloc[259:]*=5
        b,_=target_schedule(r,SECTOR_MAP,cfg)
        for name in STRATEGIES:
            np.testing.assert_allclose(a[name].iloc[0],b[name].iloc[0],atol=1e-12)
        self.assertTrue((audit.training_end<audit.execution_date).all())
        self.assertTrue((audit.execution_date<audit.return_date).all())

    def test_missing_prices_fail(self):
        with self.assertRaises(ValueError):
            validate_prices(pd.DataFrame({'A':[1,np.nan]},index=pd.date_range('2024-01-01',periods=2)))

    def test_infeasible_caps_fail(self):
        with self.assertRaises(ValueError):
            target_weights(self.returns,'Min variance (sample)',SECTOR_MAP,replace(Config(),stock_cap=.01))

    def test_higher_cost_reduces_terminal_wealth(self):
        r=self.returns.iloc[-60:]
        t=pd.DataFrame(1/20,index=r.index[::20],columns=r.columns)
        a,_,_=simulate(r,t,0); b,_,_=simulate(r,t,25)
        self.assertLess(np.prod(1+b),np.prod(1+a))

if __name__=='__main__':
    unittest.main()
