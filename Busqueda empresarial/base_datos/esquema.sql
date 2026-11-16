-- El texto completo de cada archivo se guarda en "contenido" con un índice FULLTEXT.
-- La columna usa utf8mb4_unicode_ci para que la búsqueda ignore mayúsculas y acentos
-- (el resto de la tabla conserva utf8mb4_bin, igual que en buscador2).
-- MySQL mantiene el índice invertido por su cuenta, así que ya no hacen falta las
-- tablas diccionario, posting y posicion.
CREATE TABLE IF NOT EXISTS documentos (
  id_documento   INT AUTO_INCREMENT PRIMARY KEY,
  nombre_archivo VARCHAR(255) NOT NULL UNIQUE,
  fecha_indexado DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  url            VARCHAR(2048) NOT NULL,
  palabras       INT NOT NULL,
  tokens         INT NOT NULL,
  tamano         INT NOT NULL,
  contenido      MEDIUMTEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  FULLTEXT INDEX ft_contenido (contenido)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
