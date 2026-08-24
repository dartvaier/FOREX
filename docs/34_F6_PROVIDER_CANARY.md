# F6.7 Provider Canary Checkpoint

Canaries are manual opt-in only and write non-sensitive summaries under `outputs/agent_canary/<id>`. Proposal-only invokes the existing provider then schema/ProposalValidator and stops. Assessment-only uses frozen facts and verifies factual preservation. Real loop eligibility requires both passing plus F6.5 safety; no holdout is used for prompt tuning. In this environment no API key is available, so real canaries remain unexecuted.
