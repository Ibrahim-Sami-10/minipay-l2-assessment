# AI Usage

AI assistance was used as an engineering aid, not as a substitute for
validation or ownership.

## Tools and tasks

- Copilot/LLM assistance: reviewed the assessment requirements, identified
  missing submission artifacts, and suggested documentation structure.
- Copilot/LLM assistance: reviewed API, support-tool, SQL, and Kubernetes
  behavior for edge cases and test coverage.
- Shell tools and pytest were used by the author to inspect, run, and verify
  every generated or modified result.

## Representative interactions

1. Asked for a requirements-to-files gap analysis against `INSTRUCTIONS.md`
   and the six assessment requirement files.
2. Asked for a review of API idempotency, authentication, validation, and
   duplicate transaction-reference handling.
3. Asked for a reproducible local and Kubernetes setup sequence.
4. Asked for a final test and Git-submission checklist.

## Validation and correction

The suggestions were checked against the actual source, manifests, and runtime.
One important correction was made during validation: the `.env` file defines
`API_KEY`, while the original API and UI test fixtures only read
`MINIPAY_API_KEY`. The fixtures were changed to accept either variable rather
than requiring a manual, undocumented rename. The API suite, UI suite, and
support-tool unit tests were then run against the local Compose deployment.
