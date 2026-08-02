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
