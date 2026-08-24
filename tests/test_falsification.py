import pytest
from research.falsification import FalsificationCriterion,FalsificationMetric,FalsificationOperator,FalsificationScope


@pytest.mark.parametrize(("operator","value","expected"),((FalsificationOperator.LT,0.9,True),(FalsificationOperator.LTE,1.2,True),(FalsificationOperator.GT,20.1,True),(FalsificationOperator.GTE,20,True)))
def test_failure_predicate_evaluates_all_operators(operator,value,expected):
    criterion=FalsificationCriterion(FalsificationMetric.SHARPE_RATIO if operator in (FalsificationOperator.LT,FalsificationOperator.LTE) else FalsificationMetric.MAXIMUM_DRAWDOWN_PERCENT,operator,1.2 if operator in (FalsificationOperator.LT,FalsificationOperator.LTE) else 20,FalsificationScope.EXPERIMENT)
    assert criterion.evaluate(value) is expected


def test_failure_predicate_rejects_non_finite_value():
    criterion=FalsificationCriterion(FalsificationMetric.SHARPE_RATIO,FalsificationOperator.LTE,1.2,FalsificationScope.EXPERIMENT)
    with pytest.raises(ValueError): criterion.evaluate(float("nan"))
