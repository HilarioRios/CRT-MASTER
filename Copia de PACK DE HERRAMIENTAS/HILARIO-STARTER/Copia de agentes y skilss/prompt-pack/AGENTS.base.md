# AGENTS.md instructions

## Skill Usage Preferences

- Always use `prompt-master` as a global prompt-quality layer for substantive work in Codex.
- Silently check whether an installed skill matches the user's intent before substantive work.
- If one or more skills clearly apply, use the smallest useful set automatically.
- When another domain skill also applies, use `prompt-master` first, then the domain skill.
- If the user asks for prompts, instructions, workflows, agent tasks, Codex tasks, Claude Code tasks, Cursor tasks, image prompts, or video prompts, use `prompt-master`.
- Do not output internal prompt blocks unless the user explicitly asks for a prompt artifact.
- When showing skills to the user, translate display names and descriptions into Spanish while preserving exact internal ids in backticks.
- Announce skill chains in Spanish when useful, for example: "Voy a usar `prompt-master` -> `seo-audit` para esto."

## Priority Skills

- `prompt-master`: prompt quality, agent instructions, workflow prompts, AI task shaping.
- `skill-router`: practical skill selection.
- `superpowers:brainstorming`: feature design, creative direction, behavior changes.
- `superpowers:writing-plans`: approved requirements into implementation plans.
- `superpowers:test-driven-development`: implementation and bugfix workflow.
- `superpowers:systematic-debugging`: bugs, failures, unexpected behavior.
- `superpowers:verification-before-completion`: verification before claiming completion.
- `superpowers:requesting-code-review`: important or multi-file change review.

## Optional Installed Stack

These tools are available but must remain optional. Use them only when the task clearly calls for them.

- `the-architect`: architecture, project structure, blueprints, and high-impact technical decisions.
- `cyber-neo`: security audits, vulnerabilities, secrets, auth, permissions, dependency risk, OWASP.
- `all-deploy`: local run, preview deploy, production deploy, Vercel/Railway/VPS routing.
- `claude-seo-ai`: deep SEO + AI-search visibility audits, schema, sitemap, robots, llms.txt, Core Web Vitals.
- `claude-ads`: Meta, Google, TikTok, paid media audits, ad landing pages, budgets, campaign creative.
- Agency Agents: specialist agent bank for Claude Code and Codex. Activate a specific specialist only when it adds clear value.

Activation rules:

1. Prefer the base skills already available.
2. Use an optional package only when it matches the user's intent.
3. Load the smallest useful set; do not stack many agents by default.
4. Ask for explicit confirmation before risky actions: deploys, security changes, account connections, ad publishing, campaign changes, or spend.
5. For small tasks, do not use specialist agents just because they are installed.

## Architect Mode

Use Architect Mode for architecture, structure, tech decisions, project setup, or product foundation work.

1. Clarify the product goal before choosing technology.
2. Separate reversible decisions from hard-to-change decisions.
3. Prefer simple structure before adding abstractions.
4. Define scope, non-goals, acceptance criteria, and verification.
5. Follow existing project patterns before introducing new ones.
6. Ask only when a reasonable assumption would create meaningful rework.

## Web Project Defaults

- Build the actual usable experience first.
- Match the UI to the product's purpose and audience.
- Keep layout responsive and avoid overlapping text or controls.
- Use existing design conventions when present.
- Verify locally when possible before saying work is complete.
- Keep edits scoped to the task.

## Working Contract

- Work end to end when feasible.
- Keep the user updated during longer work.
- Never revert user changes without explicit permission.
- Do not delete files, install dependencies, or perform destructive actions unless clearly required.
- Before finishing, report what changed and how it was verified.
