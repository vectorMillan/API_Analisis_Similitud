Create database verano_cientifico;
use verano_cientifico;

-- Tabla para guardar los datos del analisis
CREATE TABLE comparacion_similitud (
    id int UNSIGNED NOT NULL AUTO_INCREMENT,
    usuario_1_id INT NOT NULL,
    usuario_2_id INT NOT NULL,
    project_id INT NOT NULL,
    
    introduccion FLOAT,
    marcoteorico FLOAT,
    metodo FLOAT,
    resultados FLOAT,
    discusion FLOAT,
    conclusiones FLOAT,
    
    secciones_similares INT, -- número de secciones que superan el umbral de tolerancia
    similitud_detectada INT, -- si tiene al menos una seccion con similitud, se colocara un 1, si no tiene ninguna seccion con similitud se colocara un 0
    status_analisis TINYINT DEFAULT 0, -- 0: no analizado, 1: analizado
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id)
);

CREATE TABLE comparacion_similitud_3 (
    id int UNSIGNED NOT NULL AUTO_INCREMENT,
    usuario_1_id INT NOT NULL,
    usuario_2_id INT NOT NULL,
    project_id INT NOT NULL,
    
    introduccion FLOAT,
    marcoteorico FLOAT,
    metodo FLOAT,
    resultados FLOAT,
    discusion FLOAT,
    conclusiones FLOAT,
    
    secciones_similares INT, -- número de secciones que superan el umbral de tolerancia
    similitud_detectada INT, -- si tiene al menos una seccion con similitud, se colocara un 1, si no tiene ninguna seccion con similitud se colocara un 0
    status_analisis TINYINT DEFAULT 0, -- 0: no analizado, 1: analizado
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id)
);

CREATE TABLE comparacion_similitud_4 (
    id int UNSIGNED NOT NULL AUTO_INCREMENT,
    usuario_1_id INT NOT NULL,
    usuario_2_id INT NOT NULL,
    project_id INT NOT NULL,
    
    introduccion FLOAT,
    marcoteorico FLOAT,
    metodo FLOAT,
    resultados FLOAT,
    discusion FLOAT,
    conclusiones FLOAT,
    
    secciones_similares INT, -- número de secciones que superan el umbral de tolerancia
    similitud_detectada INT, -- si tiene al menos una seccion con similitud, se colocara un 1, si no tiene ninguna seccion con similitud se colocara un 0
    status_analisis TINYINT DEFAULT 0, -- 0: no analizado, 1: analizado
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id)
);

CREATE TABLE comparacion_similitud_5 (
    id int UNSIGNED NOT NULL AUTO_INCREMENT,
    usuario_1_id INT NOT NULL,
    usuario_2_id INT NOT NULL,
    project_id INT NOT NULL,
    
    introduccion FLOAT,
    marcoteorico FLOAT,
    metodo FLOAT,
    resultados FLOAT,
    discusion FLOAT,
    conclusiones FLOAT,
    
    secciones_similares INT, -- número de secciones que superan el umbral de tolerancia
    similitud_detectada INT, -- si tiene al menos una seccion con similitud, se colocara un 1, si no tiene ninguna seccion con similitud se colocara un 0
    status_analisis TINYINT DEFAULT 0, -- 0: no analizado, 1: analizado
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id)
);

CREATE TABLE estadistica_tm (
    id int UNSIGNED NOT NULL AUTO_INCREMENT,
    project_id INT NOT NULL,
    usuario_1_id INT NOT NULL,
    introduccion_u1 int,
    marcoteorico_u1 int,
    metodo_u1 int,
    resultados_u1 int,
    discusion_u1 int,
    conclusiones_u1 int,
    palabras_tm_u1 text,
    
    usuario_2_id INT NOT NULL,
    introduccion_u2 int,
    marcoteorico_u2 int,
    metodo_u2 int,
    resultados_u2 int,
    discusion_u2 int,
    conclusiones_u2 int,
    palabras_tm_u2 text,

    PRIMARY KEY (id)
);

-- Tabla para ajustar_tolerancias
CREATE TABLE tolerancias_similitud (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT,          -- Identificador único de la configuración
  seccion VARCHAR(50) NOT NULL,                       -- Nombre de la sección (ej: 'introduccion', 'marcoteorico', etc.)
  tolerancia FLOAT NOT NULL,                   -- Valor del porcentaje de tolerancia permitido (por ejemplo, 0.5 para 50%)
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_seccion (seccion)                     -- Evita duplicidad para una misma sección
)

-- Consultas

-- Consulta para resumen de proyectos
SELECT 
  p.name AS nombre_proyecto,
  COUNT(DISTINCT rf.user_id) AS num_integrantes,

  -- Conteo de comparaciones donde se detectó similitud
  (
    SELECT COUNT(*)
    FROM comparacion_similitud cs
    WHERE cs.project_id = p.id
      AND cs.similitud_detectada = 1
  ) AS similitud_reportes,

  -- Verifica si todas las comparaciones fueron analizadas
  CASE
    WHEN (
      SELECT MIN(cs2.status_analisis)
      FROM comparacion_similitud cs2
      WHERE cs2.project_id = p.id
    ) = 1 THEN '✅'
    ELSE '❌'
  END AS analizado

FROM project p
JOIN reportes_finales rf 
  ON rf.project_id = p.id

WHERE p.id_thematic = 2    -- ← Filtro por temática 5

GROUP BY 
  p.id, 
  p.name;
  
  -- Consulta para detalles por proyectos
  SELECT
  CONCAT(
    u1.name, ' ', u1.falastname, ' ', u1.molastname,
    ' vs ',
    u2.name, ' ', u2.falastname, ' ', u2.molastname
  ) AS usuarios_analizados,
  cs.introduccion,
  cs.marcoteorico,
  cs.metodo,
  cs.resultados,
  cs.discusion,
  cs.conclusiones,
  cs.secciones_similares
FROM comparacion_similitud cs
JOIN `user` u1
  ON cs.usuario_1_id = u1.id
JOIN `user` u2
  ON cs.usuario_2_id = u2.id
WHERE cs.project_id = 1093
ORDER BY cs.id;
