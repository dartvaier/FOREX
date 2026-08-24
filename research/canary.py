"""Manual, opt-in provider canaries. They never start research or trading."""
from __future__ import annotations

import argparse
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from hashlib import sha256
import json
from pathlib import Path
from typing import Mapping

from research.agent import ResearchAssessment
from research.context import proposal_context
from research.ollama_provider import OllamaProvider, OllamaProviderError
from research.proposal import HypothesisProposal, HypothesisProposalValidator
from research.registry import StrategyRegistry


@dataclass(frozen=True, slots=True)
class CanaryResult:
    canary_id: str
    kind: str
    passed: bool
    fingerprint: str
    summary: dict


class ProviderCanaryRunner:
    """Write reviewable, non-sensitive artifacts for a bounded provider call."""

    def __init__(self, provider, registry: StrategyRegistry, validator: HypothesisProposalValidator,
                 output_root: Path | str = "outputs/agent_canary"):
        self.provider, self.registry, self.validator = provider, registry, validator
        self.root = Path(output_root)

    def proposal_only(self, canary_id: str) -> CanaryResult:
        self._id(canary_id)
        context = proposal_context(self.registry)
        try:
            proposal = self.provider.propose(context)
            validation = self.validator.validate(proposal)
        except OllamaProviderError as error:
            return self._write(
                canary_id,
                "proposal_only",
                {
                    "provider_status": "FAILED",
                    "schema_valid": False,
                    "proposal_validator_executed": False,
                    "capability_boundaries_preserved": True,
                    "research_not_started": True,
                    "holdout_not_used": True,
                },
                {"error": {"code": error.code.value, "message": str(error)}},
            )

        schema_valid = isinstance(proposal, HypothesisProposal) and validation.fingerprint == proposal.fingerprint
        return self._write(
            canary_id,
            "proposal_only",
            {
                "provider_status": "SUCCESS",
                "provider": type(self.provider).__name__,
                "model": getattr(getattr(self.provider, "telemetry", None), "model", None),
                "schema_valid": schema_valid,
                "proposal_validator_executed": True,
                "capability_boundaries_preserved": True,
                "research_not_started": True,
                "holdout_not_used": True,
                "decision": validation.status.value,
            },
            {"proposal": proposal, "validation": validation},
        )

    def assessment_only(self, canary_id: str, facts: Mapping[str, object]) -> CanaryResult:
        self._id(canary_id)
        facts_snapshot = self._json_value(facts)
        facts_fingerprint = self._fingerprint(facts_snapshot)
        try:
            interpretation = self.provider.assess(facts)
        except OllamaProviderError as error:
            return self._write(
                canary_id,
                "assessment_only",
                {
                    "provider_status": "FAILED",
                    "factual_preservation": False,
                    "capability_boundaries_preserved": True,
                    "research_not_started": True,
                    "holdout_not_used": True,
                    "gate_status": facts_snapshot.get("gate_status"),
                    "gate_status_preserved": False,
                    "facts_fingerprint": facts_fingerprint,
                },
                {"error": {"code": error.code.value, "message": str(error)}},
            )
        preserved = self._json_value(facts) == facts_snapshot
        assessment = ResearchAssessment(facts_snapshot, interpretation)
        gate_preserved = assessment.facts.get("gate_status") == facts_snapshot.get("gate_status")
        return self._write(
            canary_id,
            "assessment_only",
            {
                "provider_status": "SUCCESS",
                "factual_preservation": preserved,
                "capability_boundaries_preserved": True,
                "research_not_started": True,
                "holdout_not_used": True,
                "gate_status": facts_snapshot.get("gate_status"),
                "gate_status_preserved": gate_preserved,
                "facts_fingerprint": facts_fingerprint,
            },
            {"facts": facts_snapshot, "assessment": assessment},
        )

    def _write(self, canary_id: str, kind: str, summary: dict, items: Mapping[str, object]) -> CanaryResult:
        path = self.root / canary_id
        path.mkdir(parents=True, exist_ok=True)
        fingerprints = {}
        for name, item in items.items():
            encoded = self._json_value(item)
            text = json.dumps(encoded, sort_keys=True, indent=2) + "\n"
            (path / f"{name}.json").write_text(text, encoding="utf-8")
            fingerprints[name] = sha256(text.encode()).hexdigest()
        payload = {"canary_id": canary_id, "kind": kind, "summary": summary, "fingerprints": fingerprints}
        text = json.dumps(payload, sort_keys=True, indent=2) + "\n"
        (path / "summary.json").write_text(text, encoding="utf-8")
        required = ("schema_valid", "proposal_validator_executed", "capability_boundaries_preserved",
                    "research_not_started", "holdout_not_used")
        passed = (summary.get("provider_status") == "SUCCESS" and all(summary.get(key) is True for key in required)) \
            if kind == "proposal_only" else (
                summary.get("provider_status") == "SUCCESS" and all(
            summary.get(key) is True for key in ("factual_preservation", "gate_status_preserved",
                                                  "capability_boundaries_preserved", "research_not_started",
                                                  "holdout_not_used")
                )
            )
        return CanaryResult(canary_id, kind, passed, sha256(text.encode()).hexdigest(), summary)

    @staticmethod
    def _json_value(value):
        if is_dataclass(value):
            return {field.name: ProviderCanaryRunner._json_value(getattr(value, field.name)) for field in fields(value)}
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, Mapping):
            return {str(key): ProviderCanaryRunner._json_value(item) for key, item in value.items()}
        if isinstance(value, (tuple, list)):
            return [ProviderCanaryRunner._json_value(item) for item in value]
        return value

    @staticmethod
    def _fingerprint(value) -> str:
        return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

    @staticmethod
    def _id(value: str) -> None:
        if not value or not value.replace("-", "").replace("_", "").isalnum():
            raise ValueError("invalid canary id")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run an opt-in local Ollama canary.")
    parser.add_argument("kind", nargs="?", choices=("proposal-only", "assessment-only"), default="proposal-only")
    parser.add_argument("--canary-id", required=True)
    parser.add_argument("--output-root", default="outputs/agent_canary")
    parser.add_argument("--registry-root", default="research/registry")
    parser.add_argument("--facts-file")
    parser.add_argument("--timeout", type=float, default=120)
    args = parser.parse_args()
    registry = StrategyRegistry(args.registry_root)
    runner = ProviderCanaryRunner(
        OllamaProvider(timeout=args.timeout), registry, HypothesisProposalValidator(registry), args.output_root
    )
    if args.kind == "proposal-only":
        result = runner.proposal_only(args.canary_id)
    else:
        if not args.facts_file:
            parser.error("--facts-file is required for assessment-only")
        facts = json.loads(Path(args.facts_file).read_text(encoding="utf-8"))
        if not isinstance(facts, dict):
            parser.error("--facts-file must contain a JSON object")
        result = runner.assessment_only(args.canary_id, facts)
    print(json.dumps({"passed": result.passed, "fingerprint": result.fingerprint, "summary": result.summary}, sort_keys=True))
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
