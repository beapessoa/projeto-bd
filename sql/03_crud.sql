-- ============================================
-- CRUD e consultas básicas (Etapa 1, item 3)
-- Placeholders %s = parâmetros vinculados (psycopg2).
-- ============================================

-- 3.1 Inserir novo atendimento (verifica se paciente, residente e preceptor existem).
-- Só insere quando os três IDs existem; caso contrário informa qual deles falhou.
-- Params (ordem): 1) data_hora  2) duracao_minutos  3) id_paciente  4) id_residente  5) id_preceptor
--   cursor.execute(sql, ('2026-07-15 10:00', 30, 1, 11, 6))
-- Retorna status: 'inserido' | 'paciente_inexistente' | 'residente_inexistente' | 'preceptor_inexistente'
WITH params AS (
    SELECT
        %s::timestamp AS data_hora,
        %s::int       AS duracao_minutos,
        %s::int       AS id_paciente,
        %s::int       AS id_residente,
        %s::int       AS id_preceptor
),
inserido AS (
    INSERT INTO atendimento
        (data_hora, duracao_minutos, id_paciente, id_residente, id_preceptor)
    SELECT p.data_hora, p.duracao_minutos, p.id_paciente, p.id_residente, p.id_preceptor
      FROM params p
     WHERE EXISTS (SELECT 1 FROM paciente  pac WHERE pac.id_pessoa       = p.id_paciente)
       AND EXISTS (SELECT 1 FROM residente res WHERE res.id_profissional = p.id_residente)
       AND EXISTS (SELECT 1 FROM preceptor pre WHERE pre.id_profissional = p.id_preceptor)
    RETURNING id_atendimento
)
SELECT CASE
           WHEN NOT EXISTS (SELECT 1 FROM paciente  pac, params p WHERE pac.id_pessoa       = p.id_paciente)  THEN 'paciente_inexistente'
           WHEN NOT EXISTS (SELECT 1 FROM residente res, params p WHERE res.id_profissional = p.id_residente) THEN 'residente_inexistente'
           WHEN NOT EXISTS (SELECT 1 FROM preceptor pre, params p WHERE pre.id_profissional = p.id_preceptor) THEN 'preceptor_inexistente'
           ELSE 'inserido'
       END                                   AS status,
       (SELECT id_atendimento FROM inserido) AS id_atendimento;


-- 3.2 Listar todos os atendimentos de um paciente, com residente e preceptor.
-- Params (ordem): 1) id_paciente
--   cursor.execute(sql, (1,))
-- Retorna: dados do atendimento + nome do residente e do preceptor, ordenado por data (mais recente primeiro).
SELECT a.id_atendimento,
       a.data_hora,
       a.duracao_minutos,
       res.nome AS residente,
       pre.nome AS preceptor
  FROM atendimento a
  JOIN pessoa res ON res.id_pessoa = a.id_residente
  JOIN pessoa pre ON pre.id_pessoa = a.id_preceptor
 WHERE a.id_paciente = %s::int
 ORDER BY a.data_hora DESC;


-- 3.3 Listar procedimentos realizados em um atendimento (nome, quantidade, tempo real).
-- Params (ordem): 1) id_atendimento
--   cursor.execute(sql, (1,))
-- Retorna: código e nome do procedimento, quantidade, tempo real, observação e se foi faturado.
SELECT proc.codigo,
       proc.nome AS procedimento,
       pr.quantidade,
       pr.tempo_real_minutos,
       pr.observacao,
       pr.faturado
  FROM procedimento_realizado pr
  JOIN procedimento proc ON proc.id_procedimento = pr.id_procedimento
 WHERE pr.id_atendimento = %s::int
 ORDER BY proc.nome;


-- 3.4 Atualizar um dado do paciente escolhendo a coluna por parâmetro.
-- Colunas permitidas: 'endereco' (pessoa) | 'num_convenio' (paciente)
--
-- Params (ordem): 1) campo  2) valor  3) id_paciente
--   cursor.execute(sql, ('endereco', 'Rua Nova, 100', 1))
--   cursor.execute(sql, ('num_convenio', 'CONV-999', 1))
WITH params AS (
    SELECT
        %s::text AS campo,
        %s::text AS valor,
        %s::int  AS id_paciente
),
upd_pessoa AS (
    UPDATE pessoa
       SET endereco = params.valor
      FROM params
     WHERE pessoa.id_pessoa = params.id_paciente
       AND params.campo = 'endereco'
       AND EXISTS (
           SELECT 1 FROM paciente
            WHERE paciente.id_pessoa = pessoa.id_pessoa
       )
    RETURNING pessoa.id_pessoa
),
upd_paciente AS (
    UPDATE paciente
       SET num_convenio = params.valor
      FROM params
     WHERE paciente.id_pessoa = params.id_paciente
       AND params.campo = 'num_convenio'
    RETURNING paciente.id_pessoa
)
SELECT id_pessoa FROM upd_pessoa
UNION ALL
SELECT id_pessoa FROM upd_paciente;


-- 3.5 Remover um procedimento realizado (somente se faturado = FALSE).
-- Params (ordem): 1) id_atendimento  2) id_procedimento
-- Retorna status: 'removido' | 'bloqueado_faturado' | 'nao_encontrado'
WITH params AS (
    SELECT %s::int AS id_atendimento, %s::int AS id_procedimento
),
alvo AS (
    SELECT pr.faturado
      FROM procedimento_realizado pr
      JOIN params p ON p.id_atendimento  = pr.id_atendimento
                   AND p.id_procedimento = pr.id_procedimento
),
removido AS (
    DELETE FROM procedimento_realizado pr
     USING params p
     WHERE pr.id_atendimento  = p.id_atendimento
       AND pr.id_procedimento = p.id_procedimento
       AND pr.faturado = FALSE
    RETURNING pr.id_atendimento
)
SELECT CASE
           WHEN NOT EXISTS (SELECT 1 FROM alvo)     THEN 'nao_encontrado'
           WHEN EXISTS     (SELECT 1 FROM removido) THEN 'removido'
           ELSE 'bloqueado_faturado'
       END AS status;


-- 3.6 Tempo médio de duração dos atendimentos por residente.
-- Retorna: residente, quantidade de atendimentos e média (min), ordenado desc.
SELECT p.nome                           AS residente,
       COUNT(a.id_atendimento)          AS qtd_atendimentos,
       ROUND(AVG(a.duracao_minutos), 1) AS tempo_medio_minutos
  FROM residente r
  JOIN pessoa      p ON p.id_pessoa    = r.id_profissional
  JOIN atendimento a ON a.id_residente = r.id_profissional
 GROUP BY p.id_pessoa, p.nome
 ORDER BY tempo_medio_minutos DESC;
