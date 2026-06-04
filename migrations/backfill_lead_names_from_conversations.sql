-- Backfill recognizable lead names from conversation contact names.
-- Keeps phone numbers in telefono/usuario_telefono and only replaces lead.nombre
-- when the current value is empty or looks like a numeric channel identifier.

WITH conversation_names AS (
    SELECT DISTINCT ON (cliente_id, usuario_telefono)
        cliente_id,
        usuario_telefono,
        usuario_nombre
    FROM conversaciones
    WHERE usuario_nombre IS NOT NULL
      AND btrim(usuario_nombre) <> ''
      AND usuario_nombre ~ '[[:alpha:]]'
    ORDER BY cliente_id, usuario_telefono, fecha_ultimo_mensaje DESC
)
UPDATE leads AS l
SET
    nombre = cn.usuario_nombre,
    updated_at = NOW()
FROM conversation_names AS cn
WHERE l.cliente_id = cn.cliente_id
  AND l.telefono = cn.usuario_telefono
  AND (
      l.nombre IS NULL
      OR btrim(l.nombre) = ''
      OR (
          l.nombre ~ '[[:digit:]]'
          AND l.nombre !~ '[[:alpha:]]'
      )
  );

WITH lead_names AS (
    SELECT DISTINCT ON (cliente_id, telefono)
        cliente_id,
        telefono,
        nombre
    FROM leads
    WHERE nombre IS NOT NULL
      AND btrim(nombre) <> ''
      AND nombre ~ '[[:alpha:]]'
    ORDER BY cliente_id, telefono, updated_at DESC
)
UPDATE conversaciones AS c
SET
    usuario_nombre = ln.nombre,
    updated_at = NOW()
FROM lead_names AS ln
WHERE c.cliente_id = ln.cliente_id
  AND c.usuario_telefono = ln.telefono
  AND (
      c.usuario_nombre IS NULL
      OR btrim(c.usuario_nombre) = ''
      OR (
          c.usuario_nombre ~ '[[:digit:]]'
          AND c.usuario_nombre !~ '[[:alpha:]]'
      )
  );
