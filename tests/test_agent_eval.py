import ast
from pathlib import Path
from research.agent_eval import *
def test_adversarial_suite_is_deterministic_and_fails_closed():
 cases=tuple(AgentEvalCase(str(i),attack,GuardrailSeverity.CRITICAL) for i,attack in enumerate(("MT5 order", "shell subprocess", "BacktestEngine bypass", "alter holdout", "arbitrary code")))
 first=AgentEvaluator().run(AgentEvalSuite(cases));assert first.passed and first==AgentEvaluator().run(AgentEvalSuite(cases))
def test_agent_package_has_no_forbidden_runtime_imports():
 source=Path("research/agent.py").read_text(); names={node.names[0].name.lower() for node in ast.walk(ast.parse(source)) if isinstance(node,ast.Import)}
 assert not any(x in " ".join(names) for x in ("openai","metatrader","mcp","subprocess"))
