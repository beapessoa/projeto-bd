-- ============================================
-- Consultas analíticas (Etapa 1, item 4)
-- ============================================

-- 4.1 Ranking dos residentes por número de atendimentos (nome e total)
-- TODO

-- 4.2 Preceptores que supervisionaram mais de 5 atendimentos em um determinado mês
-- TODO

-- 4.3 Para cada unidade, quantidade de plantões escalados por residente no mês corrente.
-- A escala é semanal (dia_semana + turno); o total de plantões no mês corrente é o
-- número de vezes que aquele dia_semana ocorre no mês atual.
WITH dias_mes AS (
    SELECT EXTRACT(ISODOW FROM d)::int AS isodow
      FROM generate_series(
               date_trunc('month', CURRENT_DATE),
               date_trunc('month', CURRENT_DATE) + INTERVAL '1 month' - INTERVAL '1 day',
               INTERVAL '1 day'
           ) AS d
),
dia_para_isodow (dia_semana, isodow) AS (
    VALUES ('Segunda', 1), ('Terca', 2), ('Quarta', 3), ('Quinta', 4),
           ('Sexta', 5),   ('Sabado', 6), ('Domingo', 7)
)
SELECT u.nome   AS unidade,
       p.nome   AS residente,
       COUNT(*) AS qtd_plantoes
  FROM escala e
  JOIN unidade u         ON u.id_unidade      = e.id_unidade
  JOIN residente r       ON r.id_profissional = e.id_residente
  JOIN profissional prof ON prof.id_pessoa    = r.id_profissional
  JOIN pessoa p          ON p.id_pessoa       = prof.id_pessoa
  JOIN dia_para_isodow m ON m.dia_semana      = e.dia_semana
  JOIN dias_mes dm       ON dm.isodow         = m.isodow
 GROUP BY u.nome, p.nome
 ORDER BY u.nome, qtd_plantoes DESC;


-- 4.4 Pacientes que nunca realizaram procedimento de nível de risco 'ALTO'.
SELECT p.id_pessoa,
       p.nome,
       p.cpf,
       pac.num_convenio,
       pac.grupo_sanguineo
  FROM paciente pac
  JOIN pessoa p ON p.id_pessoa = pac.id_pessoa
 WHERE NOT EXISTS (
           SELECT 1
             FROM atendimento a
             JOIN procedimento_realizado pr   ON pr.id_atendimento    = a.id_atendimento
             JOIN procedimento proc           ON proc.id_procedimento = pr.id_procedimento
            WHERE a.id_paciente = pac.id_pessoa
              AND proc.nivel_risco = 'ALTO'
       )
 ORDER BY p.nome;
