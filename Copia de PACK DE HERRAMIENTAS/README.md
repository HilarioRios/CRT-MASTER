# HILARIO AI DEV SYSTEM

Sistema reusable para arrancar cualquier proyecto nuevo con un ecosistema profesional de Claude Code, sin reconfigurar todo desde cero cada vez.

## Principio

- **GLOBAL** (`~/.claude`, fuera de este repo) = el taller completo: hooks de seguridad, MCPs, skills, agentes, plugins. Se documenta acá, no se versiona acá.
- **`HILARIO-STARTER/`** (dentro de este repo) = la mochila portable: se copia (`./HILARIO-STARTER/install.sh /ruta/al/proyecto`) a cada proyecto nuevo con `AGENTS.md`, `CLAUDE.md`, reglas y guardrails de proyecto.

Muchas capacidades instaladas, pocas cargadas siempre — routing y activación bajo demanda.

## Estructura

```
Replica/
├── README.md                     (este archivo)
├── docs/
│   ├── AI-SYSTEM/                 documentación completa (inventario, hooks, MCPs, routing, seguridad...)
│   └── superpowers/               spec + plan de cómo se construyó este sistema
├── HILARIO-STARTER/                la plantilla portable — ver su propio README.md
└── Copia de agentes y skilss/     prompt-pack original, preservado como referencia histórica
```

## Por dónde empezar

- ¿Querés entender qué hay instalado y por qué? → [docs/AI-SYSTEM/README.md](docs/AI-SYSTEM/README.md)
- ¿Querés arrancar un proyecto nuevo con esta base? → [HILARIO-STARTER/README.md](HILARIO-STARTER/README.md)
- ¿Algo no anda? → [docs/AI-SYSTEM/TROUBLESHOOTING.md](docs/AI-SYSTEM/TROUBLESHOOTING.md)
