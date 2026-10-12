# Loom Course Videos Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reproducir las 14 clases CRT desde Loom manteniendo navegación, progreso y bloqueo de la clase 4.

**Architecture:** `resolveVideo` normalizará los enlaces de Loom en una fuente `kind: 'loom'`. `VideoPlayer` reutilizará la portada actual y montará el iframe oficial al reproducir; los datos públicos irán en el playlist y la clase 4 seguirá llegando desde la variable de entorno protegida.

**Tech Stack:** React 18, Vite 5, Vitest 2, iframe oficial de Loom, Vercel CLI.

---

### Task 1: Resolver fuentes Loom

**Files:**
- Modify: `tests/video.test.js`
- Modify: `src/lib/video.js`

- [x] **Step 1: Escribir pruebas fallidas para URL compartida, URL embebida y resolución**

```js
expect(parseLoomId('https://www.loom.com/share/32a18566e0b84bbb8ac4d93b7d7f2db1')).toBe('32a18566e0b84bbb8ac4d93b7d7f2db1');
expect(parseLoomId('https://www.loom.com/embed/32a18566e0b84bbb8ac4d93b7d7f2db1')).toBe('32a18566e0b84bbb8ac4d93b7d7f2db1');
expect(resolveVideo({ loom: 'https://www.loom.com/share/32a18566e0b84bbb8ac4d93b7d7f2db1', poster: '/p.gif' })).toEqual({
  kind: 'loom',
  id: '32a18566e0b84bbb8ac4d93b7d7f2db1',
  embedUrl: 'https://www.loom.com/embed/32a18566e0b84bbb8ac4d93b7d7f2db1',
  poster: '/p.gif',
});
```

- [x] **Step 2: Ejecutar `npm test -- tests/video.test.js` y confirmar que falla por `parseLoomId` inexistente**
- [x] **Step 3: Implementar `parseLoomId` y la rama Loom de `resolveVideo`**
- [x] **Step 4: Repetir la prueba y confirmar que pasa**

### Task 2: Renderizar Loom y migrar datos

**Files:**
- Modify: `src/components/VideoPlayer.jsx`
- Modify: `src/data/playlists/crt.json`
- Modify: `src/data/courses.js`
- Modify: `src/pages/LessonPage.jsx`
- Modify: `tests/data.test.js`

- [x] **Step 1: Agregar una prueba que exija `lesson.video.loom` en las 14 clases públicas o protegidas y ausencia de YouTube en las clases**
- [x] **Step 2: Ejecutar `npm test -- tests/data.test.js` y confirmar el fallo por datos YouTube**
- [x] **Step 3: Reemplazar el playlist por los enlaces y miniaturas Loom; mantener vacía la URL pública de la clase 4**
- [x] **Step 4: Construir `{ loom, file, poster }`, asignar `gate.video` a `loom` y renderizar:**

```jsx
if (source.kind === 'loom') {
  if (playing) {
    return (
      <div className="video">
        <iframe src={source.embedUrl} title={title} allow="autoplay; fullscreen; picture-in-picture" allowFullScreen />
      </div>
    );
  }
}
```

- [x] **Step 5: Ejecutar `npm test -- tests/data.test.js tests/video.test.js` y confirmar que pasa**

### Task 3: Actualizar texto legal y secreto de Vercel

**Files:**
- Modify: `src/pages/Privacy.jsx`
- External configuration: Vercel variable `RESOURCE_VIDEO_CRT_C4`

- [x] **Step 1: Cambiar la descripción del proveedor de video para incluir Loom en las clases y YouTube en la VSL**
- [x] **Step 2: Actualizar `RESOURCE_VIDEO_CRT_C4` con el enlace de Loom en producción, único entorno configurado para las variables protegidas**
- [x] **Step 3: Verificar la variable por nombre y entorno sin imprimir su valor en la salida de entrega**

### Task 4: Verificar y publicar

**Files:**
- No source files adicionales.

- [x] **Step 1: Ejecutar `npm test` y exigir cero fallos**
- [x] **Step 2: Ejecutar `npm run build` y exigir salida exitosa**
- [x] **Step 3: Ejecutar `vercel --prod --yes` desde la carpeta enlazada**
- [x] **Step 4: Abrir `https://gustavo-crt.vercel.app/school/crt/el-punto-de-partida` y confirmar que el iframe apunta a Loom**
- [x] **Step 5: Confirmar que `/school` sigue mostrando 14 clases y la clase 2 continúa bloqueada antes de completar la 1**

## Nota de control de versiones

Esta carpeta no es un repositorio Git, por lo que no hay pasos de commit. El alcance excluye crear o conectar un repositorio nuevo.
