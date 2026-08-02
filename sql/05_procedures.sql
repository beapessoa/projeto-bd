-- ============================================
-- Stored Procedures (Etapa 2, requisito 1)
-- ============================================

-- Pré-requisito de sp_calcular_tempo_medio_espera (issue 2): procedimento_realizado
-- não tem timestamp próprio (tempo_real_minutos é duração, não horário), então não dá
-- para calcular "tempo até o início do procedimento" sem essa coluna.
ALTER TABLE procedimento_realizado
    ADD COLUMN IF NOT EXISTS hora_inicio TIMESTAMP;

-- Outro pré-requisito de sp_calcular_tempo_medio_espera: 
-- tempo médio de espera "para cada unidade"
-- A mesma coluna é usada pela vw_estatisticas_atendimentos_mensal (issue 6).
-- Nullable de propósito: com NOT NULL o ALTER quebraria nos atendimentos já existentes.
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
-- Não há bloco EXCEPTION nem COMMIT/ROLLBACK explícitos de propósito: um CALL é
-- executado como uma única transação implícita, então qualquer erro não tratado
-- (ex.: FK inválida de id_procedimento) já reverte automaticamente tudo o que essa
-- procedure inseriu, incluindo o atendimento. Um bloco EXCEPTION que capturasse o
-- erro sem RAISE faria o oposto do pedido (mascararia a falha e manteria o insert).


-- --------------------------------------------
-- sp_calcular_tempo_medio_espera
-- --------------------------------------------
-- Para cada unidade, o tempo médio (em minutos) entre a chegada do paciente
-- (atendimento.data_hora) e o início do PRIMEIRO procedimento daquele atendimento
-- (menor procedimento_realizado.hora_inicio).
--
-- Atendimentos sem nenhum hora_inicio preenchido são ignorados no cálculo — não dá
-- para saber quanto o paciente esperou se ninguém registrou quando o procedimento
-- começou. Unidades sem nenhum atendimento nessa condição aparecem mesmo assim, com
-- qtd_atendimentos = 0 e tempo_medio_espera_minutos NULL (o enunciado pede "para
-- cada unidade", então some-las esconderia informação).
--
-- Procedure (não função) por exigência do enunciado; como procedure no PostgreSQL não
-- tem RETURNS TABLE, o resultado sai por um REFCURSOR — daí o BEGIN/COMMIT no exemplo
-- abaixo (um cursor só existe dentro da transação que o abriu).
--
-- Parâmetros:
--   p_resultado  INOUT REFCURSOR - nome do cursor com o resultado
--                                  (default 'cur_tempo_medio_espera')
--
-- Colunas do cursor:
--   id_unidade, unidade, qtd_atendimentos, tempo_medio_espera_minutos
--
-- Exemplo de chamada (via psql):
--   BEGIN;
--   CALL sp_calcular_tempo_medio_espera();
--   FETCH ALL FROM cur_tempo_medio_espera;
--   COMMIT;
--
-- Com nome de cursor próprio (útil para chamar duas vezes na mesma transação):
--   BEGIN;
--   CALL sp_calcular_tempo_medio_espera('meu_cursor');
--   FETCH ALL FROM meu_cursor;
--   COMMIT;
--
-- Resultado esperado com os dados de sql/02_seed.sql:
--   id_unidade |            unidade            | qtd_atendimentos | tempo_medio_espera_minutos
--            4 | Ambulatório de Especialidades |                3 |                      45.00
--            1 | Enfermaria A                  |                3 |                      30.00
--            3 | Pronto-Socorro Central        |                5 |                      13.60
--            2 | UTI Geral                     |                2 |                       6.50
--   (a UTI tem 3 atendimentos no seed, mas um deles — o 14 — está sem hora_inicio)
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
-- Move TODAS as escalas de um residente de um dia/turno para outro dia/turno,
-- mantendo a unidade e o preceptor de cada uma.
--
-- Antes de alterar qualquer linha, valida que o remanejamento não gera conflito com
-- a regra de plantão único (uq_escala_plantao: id_unidade + dia_semana + turno +
-- id_residente). Se qualquer uma das escalas colidir com um plantão já existente no
-- destino, a procedure levanta exceção e NENHUMA escala é movida — a validação é
-- feita antes do UPDATE, e o CALL roda em transação única, então não há meio-termo.
--
-- Parâmetros:
--   p_id_residente        INTEGER       - FK residente
--   p_dia_origem          VARCHAR       - dia atual  ('Segunda'..'Domingo')
--   p_turno_origem        VARCHAR       - turno atual ('Manha','Tarde','Noite')
--   p_dia_destino         VARCHAR       - novo dia
--   p_turno_destino       VARCHAR       - novo turno
--   p_qtd_reajustadas     INOUT INTEGER - devolve quantas escalas foram movidas
--
-- Erros levantados:
--   - residente inexistente
--   - dia/turno de destino fora dos valores aceitos pelo CHECK da tabela
--   - origem igual ao destino
--   - nenhuma escala do residente no dia/turno de origem
--   - conflito: o residente já tem plantão naquela unidade no dia/turno de destino
--
-- Exemplo de chamada (caso válido — no seed, o residente 11 tem Segunda/Manha na
-- unidade 3 e ninguém ocupa Quinta/Noite lá):
--   CALL sp_reajustar_escala(11, 'Segunda', 'Manha', 'Quinta', 'Noite', NULL);
--   -- NOTICE: Residente 11: 1 escala(s) movida(s) de Segunda / Manha para Quinta / Noite.
--
-- Exemplo de conflito (no seed, o residente 13 tem Terca/Noite E Sabado/Manha na
-- MESMA unidade 1 — mover o plantão de terça para sábado duplicaria o plantão):
--   CALL sp_reajustar_escala(13, 'Terca', 'Noite', 'Sabado', 'Manha', NULL);
--   -- ERROR: Conflito de escala: residente 13 já tem plantão em Sabado / Manha
--   --        na unidade "Enfermaria A". Nenhuma escala foi alterada.
--
-- Atenção ao caso "conflito parcial": se o residente tem duas escalas na origem e
-- só uma delas colide no destino, NENHUMA das duas é movida (all-or-nothing).
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
