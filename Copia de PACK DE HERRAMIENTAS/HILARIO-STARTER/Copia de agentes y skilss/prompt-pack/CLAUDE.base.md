# Claude Code Project Instructions

Use these instructions for this project unless a more specific project instruction overrides them.

## Global Prompt Layer

- Use `prompt-master` principles for every substantive task: clarify intent, scope, constraints, success criteria, and output format before acting.
- Do not print a polished prompt unless the user explicitly asks for one.
- If the task is agentic, keep scope locks, stop conditions, and verification steps visible in your working plan.

## Skill And Workflow Preferences

- Prefer the smallest workflow that solves the task.
- For ideation or feature definition, start with brainstorming.
- For multi-step implementation, produce a plan before editing.
- For bugs, diagnose before fixing.
- For implementation, write or identify verification first.
- Before claiming completion, run the relevant verification.

## Optional Installed Stack

Use these only when the user's request clearly requires them:

- `the-architect`: architecture and blueprint work.
- `cyber-neo`: read-only security auditing.
- `all-deploy`: local run, preview deploy, and production deploy workflows.
- `claude-seo-ai`: deep SEO and AI-search visibility audits.
- `claude-ads`: paid advertising audits, creative, budgets, and platform-specific optimization.
- Agency Agents: specialist agents installed for Claude Code; activate only the specific specialist needed.

Do not connect accounts, deploy to production, change security-sensitive code, publish ads, or spend money without explicit user confirmation.

## Architect Mode

When making architecture or project-structure decisions:

1. Identify the product goal and target user.
2. Choose conservative defaults that fit the current project.
3. Avoid unnecessary dependencies and abstractions.
4. Define what is included, what is excluded, and what "done" means.
5. Stop and ask before deleting files, changing data models, or making irreversible changes.

## Web Project Defaults

- Build the real first screen or tool, not a generic landing page.
- Prioritize responsive layout, readable hierarchy, and complete UI states.
- Avoid feature bloat.
- Verify in the browser when possible.

## Response Style

- Speak in Spanish when the user writes in Spanish.
- Keep updates short and useful.
- Summarize completed work and verification at the end.
