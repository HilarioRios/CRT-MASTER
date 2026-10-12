# Stack Opcional De Skills Y Agentes

Este archivo documenta el stack opcional recomendado. Que este instalado no significa que deba usarse siempre.

## Regla General

Usar la herramienta minima necesaria para cumplir el pedido. No cargar varios agentes si una skill base alcanza.

## Piezas

- `prompt-master`: siempre como capa silenciosa de calidad para trabajo sustantivo.
- `skill-router`: elegir skills sin cargar inventarios innecesarios.
- `the-architect`: cuando haya que disenar arquitectura, estructura, blueprint o estrategia tecnica.
- `cyber-neo`: cuando haya que auditar seguridad o buscar vulnerabilidades.
- `all-deploy`: cuando haya que correr localmente, preparar preview o publicar un proyecto.
- `claude-seo-ai`: cuando haya que hacer auditoria profunda de SEO y visibilidad en buscadores IA.
- `claude-ads`: cuando haya trabajo serio de paid ads, Meta, Google, TikTok, presupuestos o creatividad.
- Agency Agents: banco de especialistas para usar de a uno o pocos, segun necesidad.

## Activacion Recomendada

- Proyecto nuevo o feature grande: `prompt-master` -> `the-architect` -> Superpowers.
- Implementacion comun: `prompt-master` -> Superpowers.
- Seguridad: `prompt-master` -> `cyber-neo`.
- SEO web: `prompt-master` -> `claude-seo-ai` o skills locales de SEO.
- Ads: `prompt-master` -> `claude-ads` o skills locales de marketing.
- Deploy: `prompt-master` -> `all-deploy`.
- Trabajo especializado: seleccionar 1 agente de Agency Agents.

## Guardrails

- Confirmar antes de deploy a produccion.
- Confirmar antes de conectar cuentas externas.
- Confirmar antes de publicar anuncios o gastar dinero.
- Confirmar antes de tocar seguridad, autenticacion, permisos o secretos.
- Mantener credenciales fuera de prompts y archivos.
