-- ============================================
-- CRUD e consultas básicas (Etapa 1, item 3)
-- Placeholders %s = parâmetros vinculados (psycopg2).
-- ============================================

-- 3.1 Inserir novo atendimento (verificando existência de paciente, residente e preceptor)
-- TODO

-- 3.2 Listar todos os atendimentos de um paciente específico (ordenados por data)
-- TODO

-- 3.3 Listar procedimentos realizados em um atendimento (nome, quantidade, tempo real)
-- TODO


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
