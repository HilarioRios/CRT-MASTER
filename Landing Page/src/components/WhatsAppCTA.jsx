import { brandConfig } from '../config/brand.js';
import { whatsappUrl } from '../lib/whatsapp.js';
import { WhatsAppIcon } from './Icons.jsx';

const VARIANTS = {
  solid: 'btn btn-wa',
  outline: 'btn btn-borde',
  fab: 'fab-wa',
};

// El único lugar que arma un link de WhatsApp. El número sale de brandConfig.
export function WhatsAppCTA({ message = brandConfig.whatsappDefaultMessage, variant = 'solid', onClick, children, className = '' }) {
  return (
    <a
      className={`${VARIANTS[variant]} ${className}`.trim()}
      href={whatsappUrl(brandConfig.whatsappNumber, message)}
      target="_blank"
      rel="noopener noreferrer"
      onClick={onClick}
    >
      <WhatsAppIcon size={variant === 'fab' ? 22 : 19} />
      <span>{children}</span>
    </a>
  );
}
