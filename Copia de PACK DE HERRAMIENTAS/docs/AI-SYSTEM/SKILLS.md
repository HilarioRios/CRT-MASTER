# Skills — catálogo clasificado

Clasificación: **CORE** (siempre relevantes, se evalúan en cada petición sustantiva) / **STARTER** (viajan en `HILARIO-STARTER`, no necesariamente cargadas) / **ON-DEMAND** (el router las activa cuando la intención matchea) / **LIBRARY** (instaladas, se activan solo si el usuario las nombra o el caso es muy específico).

## CORE

- `prompt-master` — capa de calidad silenciosa, siempre primero.
- `skill-router` — elige hasta 2 domain skills, siempre segundo.
- `superpowers:using-superpowers` — establece cómo usar el resto de Superpowers.
- `superpowers:brainstorming`, `writing-plans`, `test-driven-development`, `systematic-debugging`, `verification-before-completion`, `requesting-code-review`, `finishing-a-development-branch` — fases del flujo estándar de crear/modificar y debug.
- `code-review`, `security-review` — skills core del producto (no del marketplace), siempre disponibles.
- `update-config` — cualquier cambio de hooks/settings.json/permisos.

## STARTER (documentadas acá, viven en `HILARIO-STARTER/.claude/`)

- `.claude/rules/security.md`, `working-contract.md`, `web-defaults.md` — no son "skills" técnicamente, son reglas de proyecto, pero cumplen el mismo rol de always-on liviano.
- `.claude/hookify.*.local.md` — guardrails de proyecto (ver `HOOKS.md`).

## ON-DEMAND (activadas por `skill-router` según intención)

- `the-architect` — arquitectura/blueprints.
- `cyber-neo` — auditoría de seguridad.
- `all-deploy` — correr local / deploy.
- `claude-seo-ai` (+ subskills: `seo-ai-crawlers`, `seo-core-web-vitals`, `seo-crawl-render`, `seo-crawlability`, `seo-ecommerce`, `seo-eeat`, `seo-entity-linking`, `seo-freshness`, `seo-geo-answerblocks`, `seo-geo-factdensity`, `seo-headings-structure`, `seo-images-media`, `seo-indexability`, `seo-internal-linking`, `seo-international`, `seo-local`, `seo-meta-onpage`, `seo-mobile`, `seo-rendering`, `seo-schema-jsonld`, `seo-score`, `seo-sitemaps`, `seo-social-cards`, `seo-vertical-detect`) — auditoría SEO/IA profunda.
- `claude-ads` (+ subskills: `ads-audit`, `ads-budget`, `ads-competitor`, `ads-create`, `ads-creative`, `ads-dna`, `ads-generate`, `ads-google`, `ads-landing`, `ads-math`, `ads-meta`, `ads-next`, `ads-photoshoot`, `ads-plan`, `ads-publish`, `ads-start`, `ads-test`, `ads-tiktok`, `ads-update`) — paid ads.
- `agent-browser` — browser automation vía CLI (complementa a los MCPs `playwright`/`chrome-devtools`).
- `dataviz`, `artifact-design`, `artifact-diagramming`, `artifact-capabilities` — cuando se publica un Artifact.
- `workflow-authoring` — solo si el usuario pidió explícitamente orquestación multiagente (`Workflow` tool).
- `the-architect:*` (blueprint-validator, blueprint-writer, stack-researcher, architect-audit, architect-brownfield, architect-next, architect-quick, architect-refresh) — sub-comandos del paquete de arquitectura.

## LIBRARY (marketing — ~65 skills, activar solo si la intención es explícitamente de marketing/growth)

`ab-test-setup`, `ad-creative`, `ai-seo`, `analytics-tracking`, `aso-audit`, `churn-prevention`, `co-marketing`, `cold-email`, `community-marketing`, `competitor-alternatives`, `competitor-profiling`, `content-strategy`, `copy-editing`, `copywriting`, `customer-research`, `directory-submissions`, `email-sequence`, `form-cro`, `free-tool-strategy`, `launch-strategy`, `lead-magnets`, `marketing-ideas`, `marketing-psychology`, `onboarding-cro`, `page-cro`, `paid-ads`, `paywall-upgrade-cro`, `popup-cro`, `pricing-strategy`, `product-marketing-context`, `programmatic-seo`, `referral-program`, `revops`, `sales-enablement`, `schema-markup`, `seo-audit`, `signup-flow-cro`, `site-architecture`, `social-content`.

## LIBRARY (otros paquetes instalados)

- HyperFrames / video: `hyperframes`, `hyperframes-cli`, `hyperframes-media`, `hyperframes-registry`, `website-to-hyperframes`, `remotion-to-hyperframes`, `video`, `gsap`, `three`, `lottie`, `waapi`, `animejs`, `css-animations`, `tailwind`, `image`, `carrusel`.
- `claude-statusbar` (+ `statusbar`, `statusbar-doctor`, `statusbar-preview`, `statusbar-reset`, `statusbar-style`, `statusbar-theme`) — ya en uso (ver la statusLine en `~/.claude/settings.json`).
- `karpathy-rules` — principios de ingeniería, referencia puntual.
- `automatic-codex-orchestration`, `codex:*` — delegación a Codex.
- Anthropic-skills sincronizadas desde claude.ai (`docs`, `docx`, `pdf`, `pptx`, `xlsx`, `import-memory`, `skill-creator`, `morning`, `linkedin-marketing`, `twitter-algorithm-optimizer`, `web-artifacts-builder`, `agente-auditor`) — no se tocan, ya gestionadas por el propio sync de claude.ai.
- `claude-seo-ai:*` y `claude-ads:*` agentes/comandos ya cubiertos arriba en ON-DEMAND.

## Descartadas / no instaladas

Ver `PLUGINS.md` para el detalle de lo que quedó en el marketplace oficial sin habilitar, y `INSTALLED.md` para `security-guidance` y los duplicados de `code-review`/`skill-creator`.
