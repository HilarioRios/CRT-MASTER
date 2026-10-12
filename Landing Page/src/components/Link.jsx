import { navigate } from '../lib/router.js';

// Link interno: navega sin recargar. Con ctrl/cmd/click medio se comporta
// como un link normal.
export function Link({ to, onClick, children, ...rest }) {
  function handleClick(event) {
    onClick?.(event);
    if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    navigate(to);
  }
  return (
    <a href={to} onClick={handleClick} {...rest}>
      {children}
    </a>
  );
}
