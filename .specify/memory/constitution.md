<!--
Sync Impact Report
==================
Version change: 1.0.0 → 1.1.0 (MINOR: new principle added)
Modified principles: None
Added sections:
  - Core Principles: VI. Test-Driven Development (TDD) — new principle
Removed sections: None
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ no changes needed
  - .specify/templates/spec-template.md ✅ no changes needed
  - .specify/templates/tasks-template.md ✅ no changes needed
  - specs/001-ai-export-analysis/plan.md ✅ updated Constitution Check
Follow-up TODOs: None
-->

# AIReportNew Constitution

## Core Principles

### I. Specification-First

Every feature MUST begin with a written specification before any implementation work begins. The specification MUST define user scenarios, functional requirements, and measurable success criteria. Specifications MUST be reviewed and approved before proceeding to implementation planning.

**Rationale**: Without a written spec, requirements drift silently. The act of writing forces clarity on scope, edge cases, and acceptance criteria — mistakes caught at spec time cost 10x less than mistakes caught in code.

### II. Simplicity by Default

Every implementation MUST be the simplest thing that satisfies the specification. Features not requested MUST NOT be built. Abstractions with a single caller MUST NOT exist. Configuration options without a concrete use case MUST NOT be added.

**Rationale**: Every line of code written is a line that must be maintained, debugged, and understood by the next contributor. The YAGNI principle ("You Aren't Gonna Need It") applies. If a 50-line solution exists, a 200-line solution is a bug, not an improvement.

### III. Think Before Coding

Before writing any code, the implementer MUST explicitly state their assumptions. When multiple interpretations of a requirement exist, they MUST be surfaced — not silently chosen. If something is unclear, work MUST stop until clarity is obtained. Confusion MUST NOT be hidden.

**Rationale**: LLM-generated code is prone to silent assumptions and plausible-but-wrong solutions. Explicit assumption-checking is the cheapest form of bug prevention.

### IV. Surgical Changes

Every change MUST touch only the code needed to satisfy the requirement. Adjacent code, comments, or formatting MUST NOT be "improved" in passing. When editing existing code, the existing style MUST be matched — even if the implementer would have done it differently. When changes create orphans (unused imports, variables, functions), only the orphans created by the change MUST be cleaned up; pre-existing dead code MUST NOT be removed without explicit authorization.

**Rationale**: Mixed-purpose diffs make code review, blame, and rollback harder. Every changed line MUST trace directly back to the requirement.

### V. Goal-Driven Execution

Every implementation task MUST define verifiable success criteria before coding begins. Tasks MUST be structured as: "Write a failing test → make it pass → verify." For multi-step tasks, a brief plan with per-step verification MUST be stated upfront. Weak criteria ("make it work") are unacceptable.

**Rationale**: A goal without a test is a wish. Verifiable criteria enable independent iteration — the implementer can loop until the criteria are met without constant external clarification.

### VI. Test-Driven Development (TDD) — NON-NEGOTIABLE

All implementation MUST follow the Red-Green-Refactor cycle strictly:

1. **Red**: Write a failing test that defines the expected behavior. The test MUST fail for the right reason before any implementation code is written.
2. **Green**: Write the minimum code to make the test pass. No speculative code beyond what the test demands.
3. **Refactor**: Clean up the code while tests stay green. Remove duplication, improve naming, simplify — but add no new behavior.

Test tasks MUST be written and verified as FAILING before their corresponding implementation tasks are executed. Every functional requirement MUST have at least one automated test. Tests MUST be runnable via a single command (`pytest`) with no manual setup.

**Rationale**: TDD is the enforcement mechanism for Principles II (Simplicity) and V (Goal-Driven Execution). Writing the test first forces the implementer to define success before coding, and the Red-Green-Refactor loop prevents speculative code. This is the single highest-leverage engineering practice for correctness and maintainability.

## Technical Constraints

- **AI Integration**: All AI-powered functionality MUST support model portability — no hard dependency on a single AI provider or model. Provider-specific code MUST be isolated behind a well-defined interface.
- **Report Generation**: Reports MUST support multiple output formats where applicable (Markdown, HTML, PDF). Report templates and rendering logic MUST be separated.
- **Observability**: AI report generation pipelines MUST log inputs, outputs, and latency at each stage for debuggability. Text I/O is preferred over binary formats where feasible.
- **Error Handling**: AI service failures MUST produce user-actionable error messages, not raw stack traces. Graceful degradation is preferred over all-or-nothing failure.

## Development Workflow

The project follows the Speckit workflow:

1. **Specify** (`/speckit-specify`): Write feature specification with user stories, requirements, and success criteria.
2. **Plan** (`/speckit-plan`): Produce implementation plan with technical context, project structure, and constitution compliance check.
3. **Tasks** (`/speckit-tasks`): Generate dependency-ordered, user-story-grouped tasks.
4. **Implement** (`/speckit-implement`): Execute tasks sequentially, verifying each before moving to the next.
5. **Analyze** (`/speckit-analyze`): Cross-artifact consistency check across spec, plan, and tasks.

All code changes MUST reference a feature specification. Ad-hoc changes without a spec are permitted only for trivial fixes (typos, configuration, documentation) and MUST be documented in the commit message.

## Governance

This Constitution is the highest authority for this project. All implementation plans, code reviews, and feature specifications MUST verify compliance with the Core Principles. Any deviation MUST be explicitly justified in the plan's Complexity Tracking table.

**Amendment Process**: Amendments require a written proposal describing the change and rationale. The proposal MUST be reviewed and approved before the constitution is updated. The version number MUST be incremented per semantic versioning rules:
- MAJOR: Backward-incompatible principle removals or redefinitions.
- MINOR: New principle or section added, or materially expanded guidance.
- PATCH: Clarifications, wording, typo fixes.

**Compliance**: Every pull request and code review MUST verify alignment with Core Principles. Complexity that violates a principle MUST be justified in writing. The Constitution Check gate in the implementation plan serves as the formal compliance checkpoint.

**Version**: 1.1.0 | **Ratified**: 2026-06-22 | **Last Amended**: 2026-06-22
