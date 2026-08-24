"""Typed, deterministic falsification contract for research proposals."""
from dataclasses import dataclass
from enum import StrEnum
from math import isfinite


class FalsificationScope(StrEnum): EXPERIMENT="EXPERIMENT"; WALK_FORWARD="WALK_FORWARD"; GATE="GATE"
class FalsificationMetric(StrEnum):
    PERCENTAGE_RETURN="percentage_return"; TRADE_COUNT="trade_count"; WIN_RATE="win_rate"; PROFIT_FACTOR="profit_factor"; SHARPE_RATIO="sharpe_ratio"; MAXIMUM_DRAWDOWN_PERCENT="maximum_drawdown_percent"
    POSITIVE_FOLD_PROPORTION="positive_fold_proportion"; MEDIAN_RETURN_PERCENT="median_return_percent"; RETURN_DISPERSION="return_dispersion"; WORST_RETURN_PERCENT="worst_return_percent"; MEDIAN_DRAWDOWN_PERCENT="median_drawdown_percent"; WORST_DRAWDOWN_PERCENT="worst_drawdown_percent"
    WALK_FORWARD_RETURN_DEGRADATION="walk_forward_return_degradation"
class FalsificationOperator(StrEnum): LT="LT"; LTE="LTE"; GT="GT"; GTE="GTE"

METRIC_SCOPES={
 FalsificationMetric.PERCENTAGE_RETURN:frozenset((FalsificationScope.EXPERIMENT,FalsificationScope.GATE)),
 FalsificationMetric.TRADE_COUNT:frozenset((FalsificationScope.EXPERIMENT,FalsificationScope.GATE)),
 FalsificationMetric.WIN_RATE:frozenset((FalsificationScope.EXPERIMENT,)),
 FalsificationMetric.PROFIT_FACTOR:frozenset((FalsificationScope.EXPERIMENT,FalsificationScope.GATE)),
 FalsificationMetric.SHARPE_RATIO:frozenset((FalsificationScope.EXPERIMENT,FalsificationScope.GATE)),
 FalsificationMetric.MAXIMUM_DRAWDOWN_PERCENT:frozenset((FalsificationScope.EXPERIMENT,FalsificationScope.GATE)),
 FalsificationMetric.POSITIVE_FOLD_PROPORTION:frozenset((FalsificationScope.WALK_FORWARD,)),
 FalsificationMetric.MEDIAN_RETURN_PERCENT:frozenset((FalsificationScope.WALK_FORWARD,)),
 FalsificationMetric.RETURN_DISPERSION:frozenset((FalsificationScope.WALK_FORWARD,)),
 FalsificationMetric.WORST_RETURN_PERCENT:frozenset((FalsificationScope.WALK_FORWARD,)),
 FalsificationMetric.MEDIAN_DRAWDOWN_PERCENT:frozenset((FalsificationScope.WALK_FORWARD,)),
 FalsificationMetric.WORST_DRAWDOWN_PERCENT:frozenset((FalsificationScope.WALK_FORWARD,)),
 FalsificationMetric.WALK_FORWARD_RETURN_DEGRADATION:frozenset((FalsificationScope.GATE,)),
}

@dataclass(frozen=True,slots=True)
class FalsificationCriterion:
 metric:FalsificationMetric; operator:FalsificationOperator; threshold:float; scope:FalsificationScope
 def __post_init__(self):
  if not isinstance(self.metric,FalsificationMetric) or not isinstance(self.operator,FalsificationOperator) or not isinstance(self.scope,FalsificationScope): raise TypeError("falsification metric, operator and scope must be typed enums")
  if not isinstance(self.threshold,(int,float)) or isinstance(self.threshold,bool) or not isfinite(self.threshold): raise ValueError("falsification threshold must be finite")
  if self.scope not in METRIC_SCOPES[self.metric]: raise ValueError("falsification metric is unavailable in this scope")
 def evaluate(self,value:float)->bool:
  """Return true exactly when this failure predicate falsifies its hypothesis."""
  if not isinstance(value,(int,float)) or isinstance(value,bool) or not isfinite(value): raise ValueError("evaluated metric value must be finite")
  return {FalsificationOperator.LT:value<self.threshold,FalsificationOperator.LTE:value<=self.threshold,FalsificationOperator.GT:value>self.threshold,FalsificationOperator.GTE:value>=self.threshold}[self.operator]
