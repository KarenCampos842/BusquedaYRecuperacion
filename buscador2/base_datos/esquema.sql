CREATE TABLE IF NOT EXISTS documentos (
  id_documento   INT AUTO_INCREMENT PRIMARY KEY,
  nombre_archivo VARCHAR(255) NOT NULL UNIQUE,
  fecha_indexado DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE IF NOT EXISTS diccionario (
  termino           VARCHAR(100) NOT NULL PRIMARY KEY,
  num_documentos    INT NOT NULL,
  total_frecuencias INT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE IF NOT EXISTS posting (
  termino        VARCHAR(100) NOT NULL,
  id_documento   INT NOT NULL,
  frecuencia     INT NOT NULL,
  nombre_archivo VARCHAR(255) NOT NULL,
  fragmento      VARCHAR(50) NOT NULL,
  PRIMARY KEY (termino, id_documento),
  INDEX idx_posting_documento (id_documento),
  CONSTRAINT fk_posting_termino FOREIGN KEY (termino) REFERENCES diccionario (termino),
  CONSTRAINT fk_posting_documento FOREIGN KEY (id_documento) REFERENCES documentos (id_documento) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
