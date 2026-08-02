-- ============================================
-- Triggers (Etapa 2, requisito 2)
-- ============================================

-- --------------------------------------------
-- trg_audita_atendimento
-- --------------------------------------------
-- Tabela de auditoria. Sem FK para atendimento: se tivesse FK (mesmo ON DELETE
-- CASCADE), apagar um atendimento apagaria também o próprio registro de auditoria
-- do DELETE, o que anula o propósito da tabela.
CREATE TABLE IF NOT EXISTS auditoria_atendimento (
    id_auditoria    SERIAL      PRIMARY KEY,
    id_atendimento  INTEGER     NOT NULL,
    operacao        VARCHAR(10) NOT NULL,
    usuario         VARCHAR(100) NOT NULL,
    data_hora       TIMESTAMP   NOT NULL DEFAULT NOW(),
    dados_antigos   JSON,
    dados_novos     JSON,

    CONSTRAINT ck_auditoria_operacao
        CHECK (operacao IN ('INSERT', 'UPDATE', 'DELETE'))
);

-- O app não tem autenticação de usuário, então "usuario" usa SESSION_USER (o role
-- da conexão com o banco) — é o único dado de "quem fez a operação" disponível hoje.
CREATE OR REPLACE FUNCTION fn_audita_atendimento()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO auditoria_atendimento (id_atendimento, operacao, usuario, dados_antigos, dados_novos)
        VALUES (NEW.id_atendimento, 'INSERT', SESSION_USER, NULL, row_to_json(NEW));
        RETURN NEW;

    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO auditoria_atendimento (id_atendimento, operacao, usuario, dados_antigos, dados_novos)
        VALUES (NEW.id_atendimento, 'UPDATE', SESSION_USER, row_to_json(OLD), row_to_json(NEW));
        RETURN NEW;

    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO auditoria_atendimento (id_atendimento, operacao, usuario, dados_antigos, dados_novos)
        VALUES (OLD.id_atendimento, 'DELETE', SESSION_USER, row_to_json(OLD), NULL);
        RETURN OLD;
    END IF;
END;
$$;

DROP TRIGGER IF EXISTS trg_audita_atendimento ON atendimento;

CREATE TRIGGER trg_audita_atendimento
    AFTER INSERT OR UPDATE OR DELETE ON atendimento
    FOR EACH ROW
    EXECUTE FUNCTION fn_audita_atendimento();


-- trg_check_sobreposicao_escala
-- Impede que o mesmo residente seja escalado no mesmo dia/turno em DUAS UNIDADES
-- DIFERENTES — ninguém está em dois lugares ao mesmo tempo.
CREATE OR REPLACE FUNCTION fn_check_sobreposicao_escala()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_unidade_conflito VARCHAR;
BEGIN
    SELECT u.nome
      INTO v_unidade_conflito
      FROM escala e
      JOIN unidade u ON u.id_unidade = e.id_unidade
     WHERE e.id_residente = NEW.id_residente
       AND e.dia_semana   = NEW.dia_semana
       AND e.turno        = NEW.turno
       AND e.id_unidade  <> NEW.id_unidade
       AND e.id_escala IS DISTINCT FROM NEW.id_escala
     LIMIT 1;

    IF FOUND THEN
        RAISE EXCEPTION
            'Sobreposição de escala: residente % já está escalado em % / % na unidade "%".',
            NEW.id_residente, NEW.dia_semana, NEW.turno, v_unidade_conflito;
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_check_sobreposicao_escala ON escala;

CREATE TRIGGER trg_check_sobreposicao_escala
    BEFORE INSERT OR UPDATE ON escala
    FOR EACH ROW
    EXECUTE FUNCTION fn_check_sobreposicao_escala();

-- --------------------------------------------
-- trg_atualiza_media_procedimentos
-- --------------------------------------------
ALTER TABLE procedimento
    ADD COLUMN IF NOT EXISTS media_tempo_procedimento NUMERIC(10,2);

CREATE OR REPLACE FUNCTION fn_atualiza_media_procedimentos()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE procedimento p
       SET media_tempo_procedimento = (
               SELECT ROUND(AVG(pr.tempo_real_minutos), 2)
                 FROM procedimento_realizado pr
                WHERE pr.id_procedimento = NEW.id_procedimento
           )
     WHERE p.id_procedimento = NEW.id_procedimento;

    RETURN NULL; 
END;
$$;

DROP TRIGGER IF EXISTS trg_atualiza_media_procedimentos ON procedimento_realizado;

CREATE TRIGGER trg_atualiza_media_procedimentos
    AFTER INSERT ON procedimento_realizado
    FOR EACH ROW
    EXECUTE FUNCTION fn_atualiza_media_procedimentos();

UPDATE procedimento p
   SET media_tempo_procedimento = sub.media
  FROM (
        SELECT id_procedimento,
               ROUND(AVG(tempo_real_minutos), 2) AS media
          FROM procedimento_realizado
         GROUP BY id_procedimento
       ) sub
 WHERE p.id_procedimento = sub.id_procedimento;

