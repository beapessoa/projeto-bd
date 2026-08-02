-- Concorrência (Etapa 2, requisito 6)

-- O version_id_col do SQLAlchemy mapeia uma coluna que precisa existir de fato.
-- DEFAULT 1 cobre as escalas já existentes e os INSERTs feitos fora do ORM (o seed).
ALTER TABLE escala
    ADD COLUMN IF NOT EXISTS version_id INTEGER NOT NULL DEFAULT 1;
