-- ============================================
-- Stored Procedures (Etapa 2, requisito 1)
-- ============================================

-- tempo_real_minutos é duração, não horário: sem esta coluna não dá para medir
-- espera. Usada por sp_calcular_tempo_medio_espera (issue 2).
ALTER TABLE procedimento_realizado
    ADD COLUMN IF NOT EXISTS hora_inicio TIMESTAMP;

-- O schema da Etapa 1 não liga atendimento a unidade. Nullable senão o ALTER quebra
-- nos atendimentos existentes. Usada também pela view mensal (issue 6).
ALTER TABLE atendimento
    ADD COLUMN IF NOT EXISTS id_unidade INTEGER;

-- ADD CONSTRAINT não aceita IF NOT EXISTS; o DO mantém o script reexecutável.
DO $do$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_atendimento_unidade'
    ) THEN
        ALTER TABLE atendimento
            ADD CONSTRAINT fk_atendimento_unidade
            FOREIGN KEY (id_unidade) REFERENCES unidade (id_unidade)
            ON UPDATE CASCADE
            ON DELETE RESTRICT;
    END IF;
END;
$do$;

CREATE INDEX IF NOT EXISTS idx_atendimento_unidade ON atendimento (id_unidade);


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
-- Sem EXCEPTION/COMMIT explícitos: o CALL já é uma transação única, então erro não
-- tratado reverte o atendimento junto com os procedimentos.


-- --------------------------------------------
-- sp_calcular_tempo_medio_espera
-- --------------------------------------------
-- Por unidade: média entre atendimento.data_hora e o hora_inicio do PRIMEIRO
-- procedimento. Atendimento sem hora_inicio é ignorado; unidade sem dado vem NULL.
--
-- Procedure não tem RETURNS TABLE no Postgres, então o resultado sai por REFCURSOR
-- (p_resultado, default 'cur_tempo_medio_espera'), válido só dentro da transação.
--
-- Exemplo:
--   BEGIN;
--   CALL sp_calcular_tempo_medio_espera();   -- ou ('meu_cursor')
--   FETCH ALL FROM cur_tempo_medio_espera;
--   COMMIT;
CREATE OR REPLACE PROCEDURE sp_calcular_tempo_medio_espera(
    INOUT p_resultado REFCURSOR DEFAULT 'cur_tempo_medio_espera'
)
LANGUAGE plpgsql
AS $$
BEGIN
    OPEN p_resultado FOR
        WITH primeiro_procedimento AS (
            SELECT pr.id_atendimento,
                   MIN(pr.hora_inicio) AS hora_inicio
              FROM procedimento_realizado pr
             WHERE pr.hora_inicio IS NOT NULL
             GROUP BY pr.id_atendimento
        )
        SELECT u.id_unidade,
               u.nome                    AS unidade,
               COUNT(pp.id_atendimento)  AS qtd_atendimentos,
               ROUND(
                   AVG(EXTRACT(EPOCH FROM (pp.hora_inicio - a.data_hora)) / 60)::NUMERIC,
                   2
               )                         AS tempo_medio_espera_minutos
          FROM unidade u
          LEFT JOIN atendimento a
                 ON a.id_unidade = u.id_unidade
          LEFT JOIN primeiro_procedimento pp
                 ON pp.id_atendimento = a.id_atendimento
         GROUP BY u.id_unidade, u.nome
         ORDER BY u.nome;
END;
$$;


-- --------------------------------------------
-- sp_reajustar_escala
-- --------------------------------------------
-- Move as escalas de um residente de um dia/turno para outro, mantendo unidade e
-- preceptor. Valida antes do UPDATE: se uma colide no destino, nenhuma é movida.
--
-- (p_id_residente, p_dia_origem, p_turno_origem, p_dia_destino, p_turno_destino,
--  INOUT p_qtd_reajustadas) — devolve quantas escalas foram movidas.
--
-- Exemplo válido (residente 11 tem Segunda/Manha na unidade 3):
--   CALL sp_reajustar_escala(11, 'Segunda', 'Manha', 'Quinta', 'Noite', NULL);
-- Exemplo de conflito (residente 13 tem Terca/Noite E Sabado/Manha na unidade 1):
--   CALL sp_reajustar_escala(13, 'Terca', 'Noite', 'Sabado', 'Manha', NULL);
CREATE OR REPLACE PROCEDURE sp_reajustar_escala(
    p_id_residente  INTEGER,
    p_dia_origem    VARCHAR,
    p_turno_origem  VARCHAR,
    p_dia_destino   VARCHAR,
    p_turno_destino VARCHAR,
    INOUT p_qtd_reajustadas INTEGER DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_unidade_conflito VARCHAR;
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM residente WHERE id_profissional = p_id_residente
    ) THEN
        RAISE EXCEPTION 'Residente % não existe.', p_id_residente;
    END IF;

    -- Validado aqui (e não só pelo CHECK da tabela) para dar mensagem de erro útil:
    -- o CHECK só dispararia no UPDATE, com uma mensagem genérica de constraint.
    IF p_dia_destino NOT IN ('Segunda','Terca','Quarta','Quinta','Sexta','Sabado','Domingo') THEN
        RAISE EXCEPTION 'Dia de destino inválido: %.', p_dia_destino;
    END IF;

    IF p_turno_destino NOT IN ('Manha','Tarde','Noite') THEN
        RAISE EXCEPTION 'Turno de destino inválido: %.', p_turno_destino;
    END IF;

    IF p_dia_origem = p_dia_destino AND p_turno_origem = p_turno_destino THEN
        RAISE EXCEPTION 'Origem e destino são o mesmo dia/turno (% / %).',
            p_dia_origem, p_turno_origem;
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM escala
         WHERE id_residente = p_id_residente
           AND dia_semana   = p_dia_origem
           AND turno        = p_turno_origem
    ) THEN
        RAISE EXCEPTION 'Residente % não possui escala em % / %.',
            p_id_residente, p_dia_origem, p_turno_origem;
    END IF;

    -- Conflito = já existe, na MESMA unidade de uma das escalas a mover, um plantão
    -- desse residente no dia/turno de destino.
    SELECT u.nome
      INTO v_unidade_conflito
      FROM escala origem
      JOIN escala destino
        ON destino.id_unidade   = origem.id_unidade
       AND destino.id_residente = origem.id_residente
       AND destino.dia_semana   = p_dia_destino
       AND destino.turno        = p_turno_destino
      JOIN unidade u
        ON u.id_unidade = origem.id_unidade
     WHERE origem.id_residente = p_id_residente
       AND origem.dia_semana   = p_dia_origem
       AND origem.turno        = p_turno_origem
     LIMIT 1;

    IF FOUND THEN
        RAISE EXCEPTION
            'Conflito de escala: residente % já tem plantão em % / % na unidade "%". Nenhuma escala foi alterada.',
            p_id_residente, p_dia_destino, p_turno_destino, v_unidade_conflito;
    END IF;

    UPDATE escala
       SET dia_semana = p_dia_destino,
           turno      = p_turno_destino
     WHERE id_residente = p_id_residente
       AND dia_semana   = p_dia_origem
       AND turno        = p_turno_origem;

    GET DIAGNOSTICS p_qtd_reajustadas = ROW_COUNT;

    RAISE NOTICE 'Residente %: % escala(s) movida(s) de % / % para % / %.',
        p_id_residente, p_qtd_reajustadas,
        p_dia_origem, p_turno_origem, p_dia_destino, p_turno_destino;
END;
$$;
