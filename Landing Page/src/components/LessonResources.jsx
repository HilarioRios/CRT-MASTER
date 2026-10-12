import { brandConfig } from '../config/brand.js';
import { track } from '../lib/analytics.js';
import { useResourceAccess } from '../lib/useResourceAccess.js';
import { fillTemplate, whatsappUrl } from '../lib/whatsapp.js';
import { LockedResource } from './LockedResource.jsx';
import { ResourceCard } from './ResourceCard.jsx';

function Resource({ resource, course, lesson }) {
  const { status, url, requestUnlock, redeem } = useResourceAccess(resource);
  const vars = { n: lesson.order, curso: course.title, clase: lesson.title, recurso: resource.title };

  if (status !== 'unlocked') {
    return (
      <LockedResource
        resource={resource}
        status={status}
        message={fillTemplate(brandConfig.whatsappUnlockMessage, vars)}
        onRequest={() => {
          requestUnlock();
          track('recurso_desbloqueo_pedido', { recurso: resource.id });
        }}
        onRedeem={async (code) => {
          const result = await redeem(code);
          if (result.ok) track('recurso_desbloqueado', { recurso: resource.id });
          return result;
        }}
      />
    );
  }

  if (url) {
    return <ResourceCard resource={resource} href={url} unlocked={resource.access === 'team'} onClick={() => track('recurso_abierto', { recurso: resource.id })} />;
  }

  // Recurso público todavía sin archivo cargado: se pide por WhatsApp, como
  // en la web original.
  return (
    <ResourceCard
      resource={resource}
      href={whatsappUrl(brandConfig.whatsappNumber, fillTemplate(brandConfig.whatsappResourceMessage, vars))}
      action="Pedir por WhatsApp"
      onClick={() => track('recurso_pedido', { recurso: resource.id })}
    />
  );
}

export function LessonResources({ course, lesson }) {
  if (!lesson.resources.length) return null;
  return (
    <section className="recursos" aria-labelledby="recursos-titulo">
      <h3 className="eyebrow recursos-titulo" id="recursos-titulo">Recursos de esta clase</h3>
      <div className="recursos-lista">
        {lesson.resources.map((resource) => (
          <Resource key={resource.id} resource={resource} course={course} lesson={lesson} />
        ))}
      </div>
    </section>
  );
}
