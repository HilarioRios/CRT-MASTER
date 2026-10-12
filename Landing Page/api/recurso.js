// POST /api/recurso en Vercel. La lógica (y su documentación) está en
// netlify/functions/recurso.js; acá solo se adapta al formato de Vercel.
import { resolveUnlock } from '../netlify/functions/recurso.js';

export default function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).end();
  let payload = null;
  try {
    payload = typeof req.body === 'string' ? JSON.parse(req.body) : req.body;
  } catch {
    // cuerpo inválido: resolveUnlock lo rechaza
  }
  const { status, body } = resolveUnlock(payload, process.env);
  res.setHeader('Cache-Control', 'no-store');
  return res.status(status).json(body);
}
