-- Lista propia de palabras vacías en español para el índice FULLTEXT.
-- InnoDB exige una tabla InnoDB con una sola columna VARCHAR llamada exactamente "value".
-- Se llena al arrancar con recursos/stopwords_es.txt y se indica con la variable de sesión
-- innodb_ft_user_stopword_table antes de crear el índice FULLTEXT.
CREATE TABLE IF NOT EXISTS stopwords_es (
  value VARCHAR(30) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
