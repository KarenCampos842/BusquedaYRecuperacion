CREATE TABLE IF NOT EXISTS documentos (
  id_documento   INT AUTO_INCREMENT PRIMARY KEY,
  nombre_archivo VARCHAR(255) NOT NULL UNIQUE,
  fecha_indexado DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  url            VARCHAR(2048) NOT NULL,
  palabras       INT NOT NULL,
  tokens         INT NOT NULL,
  tamano         INT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE IF NOT EXISTS diccionario (
  termino           VARCHAR(100) NOT NULL PRIMARY KEY,
  id_token          INT NOT NULL AUTO_INCREMENT UNIQUE,
  num_documentos    INT NOT NULL,
  total_frecuencias INT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE IF NOT EXISTS posting (
  id_posting     BIGINT AUTO_INCREMENT PRIMARY KEY,
  termino        VARCHAR(100) NOT NULL,
  id_token       INT NOT NULL,
  id_documento   INT NOT NULL,
  frecuencia     INT NOT NULL,
  nombre_archivo VARCHAR(255) NOT NULL,
  fragmento      VARCHAR(50) NOT NULL,
  UNIQUE KEY uq_posting (termino, id_documento),
  INDEX idx_posting_documento (id_documento),
  CONSTRAINT fk_posting_termino FOREIGN KEY (termino) REFERENCES diccionario (termino),
  CONSTRAINT fk_posting_token FOREIGN KEY (id_token) REFERENCES diccionario (id_token),
  CONSTRAINT fk_posting_documento FOREIGN KEY (id_documento) REFERENCES documentos (id_documento) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE IF NOT EXISTS posicion (
  id_posicion  BIGINT AUTO_INCREMENT PRIMARY KEY,
  id_posting   BIGINT NOT NULL,
  id_token     INT NOT NULL,
  id_documento INT NOT NULL,
  posicion     INT NOT NULL,
  INDEX idx_posicion_posting (id_posting),
  INDEX idx_posicion_documento (id_documento),
  CONSTRAINT fk_posicion_posting FOREIGN KEY (id_posting) REFERENCES posting (id_posting) ON DELETE CASCADE,
  CONSTRAINT fk_posicion_token FOREIGN KEY (id_token) REFERENCES diccionario (id_token),
  CONSTRAINT fk_posicion_documento FOREIGN KEY (id_documento) REFERENCES documentos (id_documento) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;