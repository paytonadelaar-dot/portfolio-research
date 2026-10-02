import unittest
from dataclasses import replace
from model import Scenario


class ReverseDCFTests(unittest.TestCase):
    def test_zero_rate_full_ramp(self):
        self.assertAlmostEqual(Scenario(discount_rate=0, ramp=(1,)*5).required_fcf(), 27)

    def test_independent_discounted_cash_flows(self):
        s = Scenario()
        pv = sum(cf / (1+s.discount_rate)**t for t, cf in enumerate(s.cash_flows(s.required_fcf())))
        self.assertAlmostEqual(pv, 0, places=10)

    def test_price_and_integration_sensitivity(self):
        s = Scenario()
        self.assertGreater(replace(s, purchase_price=150).required_fcf(), s.required_fcf())
        self.assertAlmostEqual(replace(s, purchase_price=135).required_fcf(),
                               replace(s, integration_cost=20).required_fcf())

    def test_discount_rate_sensitivity(self):
        self.assertGreater(Scenario(discount_rate=.16).required_fcf(), Scenario(discount_rate=.08).required_fcf())

    def test_shifted_five_year_stream(self):
        s = Scenario()
        delayed = replace(s, ramp=(0, *s.ramp))
        self.assertAlmostEqual(delayed.required_fcf(), s.required_fcf() * 1.12)

    def test_fixed_horizon_delay_more_costly(self):
        s = Scenario()
        self.assertGreater(replace(s, ramp=(0, *s.ramp[:-1])).required_fcf(),
                           replace(s, ramp=(0, *s.ramp)).required_fcf())

    def test_no_terminal_value_horizon(self):
        s = Scenario()
        self.assertLess(replace(s, ramp=(*s.ramp, 1, 1)).required_fcf(), s.required_fcf())

    def test_invalid_inputs(self):
        for kwargs in ({'discount_rate':-.1}, {'purchase_price':-1}, {'ramp':(0,0)},
                       {'ramp':(1.1,)}, {'integration_cost':float('nan')}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                Scenario(**kwargs)


if __name__ == '__main__':
    unittest.main()
