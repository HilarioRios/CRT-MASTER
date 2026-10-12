# Instrucciones Base Del Proyecto

## Capa Global

- Usar `prompt-master` como capa de calidad para todo trabajo sustantivo.
- Antes de responder o ejecutar, identificar si aplica alguna skill instalada.
- Si aplica otra skill de dominio, usar primero `prompt-master` y luego la skill especifica.
- Mantener respuestas en espanol cuando el usuario escriba en espanol.
- Cuando se mencionen skills al usuario, traducir su descripcion a espanol y conservar el id interno exacto entre backticks.
- No mostrar prompts internos salvo que el usuario pida explicitamente un prompt copiable.

## Skills Prioritarias

- `prompt-master`: mejora instrucciones, prompts, delegaciones, workflows y tareas para agentes.
- `skill-router`: decide que skill usar sin cargar inventarios innecesarios.
- `superpowers:brainstorming`: para definir features, componentes, comportamiento o direccion creativa antes de construir.
- `superpowers:writing-plans`: para convertir requisitos aprobados en un plan de ejecucion.
- `superpowers:test-driven-development`: para implementar features o fixes con verificacion temprana.
- `superpowers:systematic-debugging`: para bugs, fallos o comportamiento inesperado.
- `superpowers:verification-before-completion`: antes de afirmar que algo esta terminado.
- `superpowers:requesting-code-review`: para revisar cambios importantes o multiarchivo.

## Stack Opcional Instalado

Estas piezas estan disponibles, pero no son obligatorias. Usarlas solo cuando la tarea lo justifique.

- `the-architect`: arquitectura, estructura de proyecto, blueprints y decisiones iniciales importantes.
- `cyber-neo`: auditoria de seguridad, vulnerabilidades, secretos, autenticacion, permisos, dependencias y OWASP.
- `all-deploy`: correr localmente, preparar preview, publicar en Vercel/Railway/VPS o cerrar el ciclo de deploy.
- `claude-seo-ai`: auditoria profunda de SEO + visibilidad en buscadores IA, schema, sitemap, robots, llms.txt y Core Web Vitals.
- `claude-ads`: auditoria y optimizacion de Meta, Google, TikTok, landing pages de ads, presupuesto y creatividad publicitaria.
- Agency Agents: banco de especialistas instalado para Claude Code y Codex. Activar un agente especifico solo cuando aporte expertise claro.

Regla de activacion:

1. Primero resolver con las skills base ya disponibles.
2. Activar una pieza opcional solo si coincide con la intencion del usuario.
3. No cargar muchos agentes a la vez; elegir el minimo util.
4. Para acciones con riesgo real, como deploy, cambios de seguridad, conexion de cuentas, publicacion de anuncios o gasto de dinero, pedir confirmacion explicita antes de ejecutar.
5. Si la tarea es pequena, no usar agentes especializados aunque esten instalados.

## Modo Arquitecto

Usar este modo cuando el usuario pida estructura, arquitectura, decisiones tecnicas o arranque de proyecto.

1. Entender el objetivo real del producto antes de elegir tecnologia.
2. Separar decisiones reversibles de decisiones dificiles de cambiar.
3. Proponer una estructura simple antes de agregar abstracciones.
4. Definir que queda incluido, que queda fuera y como se verifica que esta listo.
5. Preferir patrones del proyecto existente por encima de inventar una arquitectura nueva.
6. Pedir aclaracion solo si una suposicion razonable puede causar retrabajo importante.

## Reglas Para Proyectos Web

- Construir la experiencia usable primero, no una pagina de marketing generica.
- Si se crea una app con frontend, cuidar layout responsive, jerarquia visual y estados esperados.
- Evitar secciones tipo landing innecesarias si el usuario pidio una herramienta, app o experiencia concreta.
- Verificar visualmente la UI cuando sea posible antes de dar por terminado.
- Mantener cambios acotados y no tocar archivos ajenos a la tarea.

## Contrato De Trabajo

- Ejecutar de punta a punta cuando sea razonable.
- Informar brevemente que se esta haciendo durante trabajos largos.
- No revertir cambios del usuario.
- No instalar dependencias, borrar archivos ni hacer cambios destructivos sin necesidad clara.
- Antes de finalizar, indicar que se cambio y como se verifico.
