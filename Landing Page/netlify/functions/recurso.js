// POST /api/recurso  { resourceId, code }  →  { url, video? }
//
// Desbloqueo real de lo que entrega el equipo (la clase 7: su video y su
// recurso). Ni el link del documento ni el id del video están en el sitio:
// viven en variables de entorno del servidor y solo se responden si el código
// es válido.
//
//   UNLOCK_CODES          códigos que reparte el equipo, separados por coma
//   RESOURCE_URL_<ID>     link privado del documento
//   RESOURCE_VIDEO_<ID>   URL de Loom del video de la clase (opcional)
//
//   <ID> = id del bloqueo en mayúsculas, guiones → guion bajo
//          (crt-c7 → RESOURCE_URL_CRT_C7 y RESOURCE_VIDEO_CRT_C7)

const normalize = (value) => (typeof value === 'string' ? value.trim().toUpperCase() : '');

export function resolveUnlock(payload, env) {
  const code = normalize(payload?.code);
  const resourceId = typeof payload?.resourceId === 'string' ? payload.resourceId : '';
  const codes = String(env.UNLOCK_CODES || '').split(',').map(normalize).filter(Boolean);
  if (!code || !resourceId || !codes.includes(code)) {
    return { status: 403, body: { error: 'invalid_code' } };
  }
  const key = resourceId.toUpperCase().replace(/[^A-Z0-9]/g, '_');
  const url = env[`RESOURCE_URL_${key}`];
  if (!url) return { status: 404, body: { error: 'resource_not_configured' } };
  const video = env[`RESOURCE_VIDEO_${key}`];
  return { status: 200, body: video ? { url, video } : { url } };
}

export async function handler(event) {
  if (event.httpMethod !== 'POST') return { statusCode: 405, body: '' };
  let payload = null;
  try {
    payload = JSON.parse(event.body || '');
  } catch {
    // cuerpo inválido: resolveUnlock lo rechaza
  }
  const { status, body } = resolveUnlock(payload, process.env);
  return {
    statusCode: status,
    headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
    body: JSON.stringify(body),
  };
}
