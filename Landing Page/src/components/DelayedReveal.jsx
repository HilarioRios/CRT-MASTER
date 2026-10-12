import { useEffect, useRef } from 'react';

// Contenido que no existe en la página hasta que `open` es true. No es un
// display:none: mientras está cerrado, sus hijos ni se montan.
//
//   animate  true cuando se acaba de abrir en esta visita (entra con fade +
//            slide y se lleva la vista hasta ahí). En una visita posterior,
//            ya abierto, aparece sin animación.
export function DelayedReveal({ open, animate = false, children }) {
  const ref = useRef(null);

  useEffect(() => {
    if (!open || !animate || !ref.current) return;
    const calm = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    ref.current.scrollIntoView({ behavior: calm ? 'auto' : 'smooth', block: 'start' });
  }, [open, animate]);

  if (!open) return null;
  return (
    <div ref={ref} className={animate ? 'reveal reveal-in' : 'reveal'}>
      {children}
    </div>
  );
}
