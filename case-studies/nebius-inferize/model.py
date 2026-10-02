"""Reverse acquisition DCF. All monetary amounts are USD millions."""
from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class Scenario:
    purchase_price: float = 125.0
    integration_cost: float = 10.0
    discount_rate: float = 0.12
    ramp: tuple[float, ...] = (0.25, 0.60, 1.0, 1.0, 1.0)

    def __post_init__(self):
        values = (self.purchase_price, self.integration_cost, self.discount_rate, *self.ramp)
        if not all(isfinite(x) for x in values):
            raise ValueError("Inputs must be finite")
        if self.purchase_price < 0 or self.integration_cost < 0 or self.discount_rate < 0:
            raise ValueError("Costs and discount rate must be nonnegative")
        if not self.ramp or any(x < 0 or x > 1 for x in self.ramp) or not any(self.ramp):
            raise ValueError("Ramp must contain factors between zero and one, with a positive benefit")

    @property
    def upfront_outlay(self):
        return self.purchase_price + self.integration_cost

    @property
    def discounted_ramp(self):
        return sum(factor / (1 + self.discount_rate) ** year
                   for year, factor in enumerate(self.ramp, start=1))

    def required_fcf(self):
        """Annual full-run-rate after-tax unlevered FCF needed for zero NPV."""
        return self.upfront_outlay / self.discounted_ramp

    def npv(self, full_run_rate_fcf):
        return -self.upfront_outlay + full_run_rate_fcf * self.discounted_ramp

    def cash_flows(self, full_run_rate_fcf):
        return (-self.upfront_outlay, *(full_run_rate_fcf * x for x in self.ramp))
