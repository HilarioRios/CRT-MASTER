# Diseño: migración de clases CRT de YouTube a Loom

## Objetivo

Reemplazar los videos de las 14 clases de CRT por sus equivalentes en Loom sin cambiar la navegación, el progreso secuencial, los recursos PDF ni el bloqueo por código de la clase 4.

## Enfoque aprobado

El reproductor existente incorporará una tercera fuente, `loom`, además de `youtube` y `file`. Los enlaces públicos de Loom se transformarán localmente en URLs `https://www.loom.com/embed/<id>`; no se agregará una dependencia porque el iframe oficial es suficiente para reproducir los videos.

Las clases 1–3 y 5–14 guardarán su enlace de Loom en `src/data/playlists/crt.json`. La clase 4 conservará el enlace fuera del bundle público: el servidor lo entregará mediante `RESOURCE_VIDEO_CRT_C4` después de validar el código. `LessonPage` asignará ese valor al campo `loom`.

## Comportamiento

- Antes de reproducir se mantiene la miniatura y el botón de reproducción actuales.
- Al hacer clic, el sitio carga el iframe de Loom y registra `clase_play`.
- Loom no expone en este proyecto los eventos de avance y finalización usados por YouTube; por eso el alumno continuará usando el botón existente “Marcar como completada”.
- El progreso secuencial y los bloqueos permanecen sin cambios.
- La clase 4 continúa protegida por código y su URL no aparece en el JavaScript público.
- La VSL de la landing conserva YouTube; el pedido solo abarca las 14 clases.

## Archivos

- `src/lib/video.js`: reconocer enlaces de Loom y producir la URL embebida.
- `src/components/VideoPlayer.jsx`: renderizar el iframe de Loom.
- `src/data/playlists/crt.json`: reemplazar fuentes y miniaturas de YouTube por Loom.
- `src/data/courses.js`: construir `video.loom` desde el playlist.
- `src/pages/LessonPage.jsx`: tratar el video secreto de la clase 4 como fuente Loom.
- `src/pages/Privacy.jsx`: indicar que las clases se alojan en Loom y que la VSL usa YouTube.
- `tests/video.test.js` y `tests/data.test.js`: cubrir resolución de Loom y datos de las clases.

## Verificación

1. Las pruebas automatizadas y el build deben finalizar sin errores.
2. La School debe mostrar 14 clases y abrir la clase 1 con un iframe de Loom.
3. Las clases posteriores deben conservar el bloqueo secuencial.
4. La clase 4 debe seguir pidiendo el código antes de entregar su video.
5. La versión publicada en `https://gustavo-crt.vercel.app/school` debe cargar el video de Loom de la clase 1.

## Despliegue

El proyecto de Vercel `gustavo-crt` está enlazado a esta carpeta local, pero no a GitHub. La publicación se hará mediante Vercel CLI desde esta carpeta. No se crea ni conecta un repositorio como parte de este cambio.
