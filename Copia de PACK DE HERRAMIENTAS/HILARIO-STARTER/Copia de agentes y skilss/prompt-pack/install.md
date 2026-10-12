# Como Instalar Este Prompt Pack En Otros Proyectos

## Opcion Recomendada: Por Proyecto

Esta es la forma mas confiable porque cada carpeta conserva sus propias reglas.

1. Abri la carpeta del proyecto.
2. Copia `prompt-pack/AGENTS.base.md` a la raiz del proyecto con el nombre `AGENTS.md`.
3. Si usas Claude Code, copia `prompt-pack/CLAUDE.base.md` a la raiz con el nombre `CLAUDE.md`.
4. Completa el contexto especifico del proyecto dentro de esos archivos.
5. Inicia un nuevo chat o sesion del agente desde esa carpeta.

## Para ChatGPT Projects O Claude Projects

1. Abri la configuracion del proyecto.
2. Pega el contenido de `prompt-pack/project-instructions.md` en las instrucciones del proyecto.
3. Completa el bloque "Contexto Del Proyecto".
4. Usa un chat nuevo dentro de ese proyecto para que las instrucciones entren desde el inicio.

## Para Cursor, Windsurf, Cline U Otros Agentes

Usa `prompt-pack/project-instructions.md` como instrucciones generales del proyecto. Si la herramienta permite reglas por repositorio, guarda una copia ahi tambien.

## Para Repetirlo En Cada Proyecto Nuevo

Conserva esta carpeta `prompt-pack` como plantilla. En cada proyecto nuevo, instala:

- `AGENTS.md` para Codex.
- `CLAUDE.md` para Claude Code.
- Instrucciones del proyecto para chats o agentes que no lean archivos locales.
- `optional-stack.md` como referencia de herramientas opcionales.

## Nota Sobre "Instalacion Global"

La instalacion global depende de cada herramienta. La forma segura y portable es instalar estas instrucciones por proyecto, porque asi no se mezclan reglas de trabajos distintos y cada proyecto mantiene su propio contexto.

## Stack Opcional Global

En esta maquina tambien puede existir un stack global de skills/agentes. Aunque este instalado, no debe activarse por defecto.

- Global si se usa en casi todos los proyectos.
- Por proyecto si depende del dominio, cliente, stack o credenciales.
- Activar solo cuando el pedido lo requiera.
