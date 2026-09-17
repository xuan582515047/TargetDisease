# Continuous PharmAgents Implementation Plan

> **For agentic workers:** Use subagent-driven-development or executing-plans to implement these tasks. Preserve the user workspace: it is not a Git repository, so Git worktrees and commits are unavailable.

**Goal:** One resumable, auditable four-stage small-molecule workflow.
**Architecture:** AnalysisRun remains the ownership and execution unit. Versioned intermediate_json checkpoints contain stage results and optimization paths. A separate database-polling worker holds a PostgreSQL advisory lock while working, so process death releases ownership and another worker resumes. No API BackgroundTasks for new runs.
**Tech Stack:** FastAPI, SQLAlchemy, PostgreSQL, Python scientific tooling, Next.js.
**Spec:** ../specs/2026-09-16-continuous-pharmagents.md

## Global Constraints
- Three paths, five rounds, original seed preserved; baseline eligible for selection.
- Exactly two manual gates; automatic mode has neither.
- No synthetic scientific scores or silent scientific fallbacks.
- Never send user credentials to subprocess arguments or persist them in results.
- Keep old records readable; new runs have workflow_version=pharmagents-v1.

## Task 1: Scientific stages
- [ ] Add backend/app/services/pipeline_stages.py and scientific adapters with explicit unavailable/error exceptions, validated results and artifact provenance.
- [ ] Interface: PharmAgentsStages(api_key, run_id); discover(disease)->targets; identify(disease, targets)->candidates; optimize(seed, history, round_number)->candidate; choose_best(seed, history)->candidate; evaluate(candidate)->assessment; report(disease, state)->markdown. Candidate id and target_uniprot bind each result to its original receptor. optimize receives fixed seed every time.
- [ ] Add tests for chemical identity, TOXRIC threshold/top-five, synthesis stopping/loops, adapter input/output rejection; run tests before/after implementation.

## Task 2: Persistent orchestration and API (root)
- [ ] Add backend/app/services/pipeline.py and backend/app/worker.py. execute_pipeline(db, run, stages) checkpoints discovery, candidates, each optimization round, each winner and PCC assessment. Stages implement Task 1 interface.
- [ ] Write tests using deterministic test-only stage doubles: auto completes with 15 rounds; permission pauses twice; restart does not repeat stored rounds; empty/invalid output fails; missing tool pauses and can retry.
- [ ] Update runs.py create/select-leads/select-targets/retry/cancel with ownership, state and selection membership validation. Use conditional transitions and per-user row locking; preserve legacy dispatch only for legacy runs.
- [ ] Add worker compose service and persistent artifacts; document startup and pending external models. Protect active projects against deletion.

## Task 3: Continuous project UI
- [ ] Extend frontend/lib/api.ts with pipeline checkpoint/assessment types and selection/retry/cancel calls.
- [ ] Add shared project-scoped pipeline detail component and route, expose all four stages, two confirmation panels, 3x5 progress, scores, synthesis/toxicity and final Markdown report.
- [ ] Replace optimization/PCC placeholders with project-linked views; direct new dashboard runs into continuous workflow; legacy results stay accessible.
- [ ] Verify typecheck and production build, check project filtering and no cross-project implicit selection.

## Task 4: Integration verification
- [ ] Run full backend tests and frontend checks. Review concurrency, credential handling, failure semantics and resumability.
- [ ] Record what was validated locally and what requires scientific weights/GPU; do not claim a completed paper reproduction from mocked tests.
