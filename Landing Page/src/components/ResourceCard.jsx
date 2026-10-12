import { ArrowIcon, DocIcon, LinkIcon, ListCheckIcon } from './Icons.jsx';

const TYPES = {
  pdf: { label: 'PDF', Icon: DocIcon },
  doc: { label: 'Documento', Icon: DocIcon },
  checklist: { label: 'Checklist', Icon: ListCheckIcon },
  template: { label: 'Plantilla', Icon: DocIcon },
  indicator: { label: 'Indicador', Icon: LinkIcon },
  link: { label: 'Enlace', Icon: LinkIcon },
  file: { label: 'Archivo', Icon: DocIcon },
};

export const resourceType = (type) => TYPES[type] || TYPES.file;

// Tarjeta de un recurso disponible. `href` abre o descarga; `action` es el
// texto del lado derecho ("Abrir", "Pedir por WhatsApp"...).
export function ResourceCard({ resource, href, action = 'Abrir', onClick, unlocked = false }) {
  const { label, Icon } = resourceType(resource.type);
  return (
    <a className="recurso" href={href} target="_blank" rel="noopener noreferrer" onClick={onClick}>
      <span className="recurso-icono"><Icon /></span>
      <span className="recurso-textos">
        <span className="recurso-tipo">{unlocked ? `${label} · Desbloqueado` : label}</span>
        <span className="recurso-titulo">{resource.title}</span>
        {resource.description && <span className="recurso-desc">{resource.description}</span>}
      </span>
      <span className="recurso-accion">
        {action} <ArrowIcon />
      </span>
    </a>
  );
}
