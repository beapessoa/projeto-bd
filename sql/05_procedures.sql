-- ============================================
-- Stored Procedures (Etapa 2, requisito 1)
-- ============================================

-- Pré-requisito de sp_calcular_tempo_medio_espera (issue 2): procedimento_realizado
-- não tem timestamp próprio (tempo_real_minutos é duração, não horário), então não dá
-- para calcular "tempo até o início do procedimento" sem essa coluna.
ALTER TABLE procedimento_realizado
    ADD COLUMN IF NOT EXISTS hora_inicio TIMESTAMP;


-- --------------------------------------------
-- sp_registrar_atendimento_completo
-- --------------------------------------------
-- Registra um atendimento e seus procedimentos realizados em uma única transação.
-- Se qualquer procedimento da lista falhar (ex.: id_procedimento inexistente),
-- a transação inteira é revertida — nem o atendimento nem os procedimentos ficam salvos.
--
-- Parâmetros:
--   p_data_hora        TIMESTAMP     - data/hora do atendimento
--   p_duracao_minutos  INTEGER       - duração total do atendimento
--   p_id_paciente      INTEGER       - FK paciente
--   p_id_residente     INTEGER       - FK residente
--   p_id_preceptor     INTEGER       - FK preceptor
--   p_procedimentos    JSONB         - array de objetos:
--       [{"id_procedimento": 1, "quantidade": 1, "tempo_real_minutos": 30,
--         "observacao": "texto opcional", "hora_inicio": "2026-07-01T08:05:00"}, ...]
--       "observacao" e "hora_inicio" são opcionais em cada item.
--   p_id_atendimento   INOUT INTEGER - devolve o id do atendimento criado
--
-- Exemplo de chamada (via psql):
--   CALL sp_registrar_atendimento_completo(
--       '2026-08-02 08:00', 30, 1, 11, 6,
--       '[{"id_procedimento": 1, "quantidade": 1, "tempo_real_minutos": 30,
--          "observacao": "Sutura em MSD", "hora_inicio": "2026-08-02T08:05:00"}]'::jsonb,
--       NULL
--   );
--
-- Cenário de falha (procedimento inexistente -> ROLLBACK total):
--   CALL sp_registrar_atendimento_completo(
--       '2026-08-02 08:00', 30, 1, 11, 6,
--       '[{"id_procedimento": 999, "quantidade": 1, "tempo_real_minutos": 30}]'::jsonb,
--       NULL
--   );
CREATE OR REPLACE PROCEDURE sp_registrar_atendimento_completo(
    p_data_hora       TIMESTAMP,
    p_duracao_minutos INTEGER,
    p_id_paciente     INTEGER,
    p_id_residente    INTEGER,
    p_id_preceptor    INTEGER,
    p_procedimentos   JSONB,
    INOUT p_id_atendimento INTEGER DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_item JSONB;
BEGIN
    INSERT INTO atendimento (data_hora, duracao_minutos, id_paciente, id_residente, id_preceptor)
    VALUES (p_data_hora, p_duracao_minutos, p_id_paciente, p_id_residente, p_id_preceptor)
    RETURNING id_atendimento INTO p_id_atendimento;

    FOR v_item IN SELECT * FROM jsonb_array_elements(COALESCE(p_procedimentos, '[]'::jsonb))
    LOOP
        INSERT INTO procedimento_realizado
            (id_atendimento, id_procedimento, quantidade, tempo_real_minutos, observacao, hora_inicio)
        VALUES (
            p_id_atendimento,
            (v_item->>'id_procedimento')::INTEGER,
            (v_item->>'quantidade')::INTEGER,
            (v_item->>'tempo_real_minutos')::INTEGER,
            v_item->>'observacao',
            (v_item->>'hora_inicio')::TIMESTAMP
        );
    END LOOP;
END;
$$;
-- Não há bloco EXCEPTION nem COMMIT/ROLLBACK explícitos de propósito: um CALL é
-- executado como uma única transação implícita, então qualquer erro não tratado
-- (ex.: FK inválida de id_procedimento) já reverte automaticamente tudo o que essa
-- procedure inseriu, incluindo o atendimento. Um bloco EXCEPTION que capturasse o
-- erro sem RAISE faria o oposto do pedido (mascararia a falha e manteria o insert).
