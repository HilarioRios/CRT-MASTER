// Miniatura con carga diferida. Si la imagen principal no existe, cae a la
// de respaldo una sola vez. (YouTube responde una miniatura gris de 120px
// cuando no tiene la de alta: por eso también se mira el ancho al cargar.)
export function Poster({ src, fallback = '', className, eager = false }) {
  function useFallback(img) {
    if (fallback && img.dataset.fallback !== 'used') {
      img.dataset.fallback = 'used';
      img.src = fallback;
    }
  }
  return (
    <img
      className={className}
      src={src}
      alt=""
      loading={eager ? 'eager' : 'lazy'}
      fetchPriority={eager ? 'high' : 'auto'}
      decoding="async"
      onLoad={(event) => {
        if (event.currentTarget.naturalWidth <= 120) useFallback(event.currentTarget);
      }}
      onError={(event) => useFallback(event.currentTarget)}
    />
  );
}
