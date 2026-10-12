import { useCallback, useEffect, useRef, useState } from 'react';
import { brandConfig } from '../config/brand.js';
import {
  LOCAL_USER,
  accessProvider,
  nextAccessRecord,
  redeemUnlockCode,
  resourceStatus,
} from './resourceAccess.js';

// Estado de acceso de un recurso (o del bloqueo de una clase) para la persona
// actual. Varios recursos pueden compartir un mismo acceso con `accessKey`:
// así un solo código abre la clase y sus recursos.
export function useResourceAccess(resource) {
  const key = resource.accessKey || resource.id;
  const [record, setRecord] = useState(undefined);
  // true mientras todavía no se leyó el acceso guardado.
  const [loading, setLoading] = useState(resource.access === 'team');
  // Último registro conocido. Va en un ref para poder guardarlo aunque la
  // respuesta del servidor llegue cuando la persona ya cambió de clase.
  const latest = useRef(undefined);
  const touched = useRef(false);

  useEffect(() => {
    let alive = true;
    latest.current = undefined;
    touched.current = false;
    setRecord(undefined);
    setLoading(resource.access === 'team');
    accessProvider
      .getRecord(LOCAL_USER, key)
      .then((saved) => {
        // Si la persona ya actuó mientras cargaba, lo suyo es más nuevo.
        if (!alive || touched.current) return;
        latest.current = saved;
        setRecord(saved);
      })
      .catch(() => {})
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [key, resource.access]);

  const apply = useCallback(
    (event) => {
      const next = nextAccessRecord(latest.current, event);
      if (next === latest.current) return;
      touched.current = true;
      latest.current = next;
      accessProvider.setRecord(LOCAL_USER, key, next);
      setRecord(next);
    },
    [key],
  );

  const requestUnlock = useCallback(() => apply({ type: 'request' }), [apply]);

  const redeem = useCallback(
    async (code) => {
      const result = await redeemUnlockCode(key, code, {
        endpoint: brandConfig.resourceUnlockEndpoint,
      });
      if (result.ok) apply({ type: 'grant', url: result.url, video: result.video });
      return result;
    },
    [apply, key],
  );

  return {
    loading,
    status: resourceStatus(resource, record),
    url: resource.access === 'team' ? record?.url : resource.url,
    video: resource.access === 'team' ? record?.video || '' : '',
    requestUnlock,
    redeem,
  };
}
