// Arma links de WhatsApp. El número y los mensajes viven en config/brand.js:
// ningún componente escribe un número a mano.

export function whatsappUrl(number, message) {
  const digits = String(number || '').replace(/\D/g, '');
  const base = `https://wa.me/${digits}`;
  return message ? `${base}?text=${encodeURIComponent(message)}` : base;
}

export function fillTemplate(template, vars) {
  return String(template).replace(/\{(\w+)\}/g, (match, key) =>
    vars[key] === undefined || vars[key] === null ? match : String(vars[key]),
  );
}
