-- ============================================
-- Views (Etapa 2, requisito 3)
-- ============================================

-- --------------------------------------------
-- Tabela internacao
-- --------------------------------------------
-- Não existia na Etapa 1 (só tínhamos atendimento, um evento pontual).
-- Mantida mínima, só com o necessário para vw_pacientes_internados funcionar:
-- entrada, saída (NULL = ainda internado) e onde.
CREATE TABLE IF NOT EXISTS internacao (
    id_internacao     SERIAL    PRIMARY KEY,
    id_paciente        INTEGER   NOT NULL,
    id_unidade         INTEGER   NOT NULL,
    data_hora_entrada  TIMESTAMP NOT NULL,
    data_hora_saida    TIMESTAMP,

    CONSTRAINT fk_internacao_paciente
        FOREIGN KEY (id_paciente) REFERENCES paciente (id_pessoa)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    CONSTRAINT fk_internacao_unidade
        FOREIGN KEY (id_unidade) REFERENCES unidade (id_unidade)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT ck_internacao_saida
        CHECK (data_hora_saida IS NULL OR data_hora_saida >= data_hora_entrada)
);

-- Dados de teste: paciente 1 ainda internado; paciente 2 já com alta.
-- Paciente 5 tem duas internações — a mais antiga ficou aberta (erro de digitação
-- comum: esqueceram de registrar a saída) e a mais recente já foi encerrada. Serve
-- pra provar que a view usa a internação MAIS RECENTE, não "existe alguma aberta".
INSERT INTO internacao (id_paciente, id_unidade, data_hora_entrada, data_hora_saida) VALUES
    (1, 2, '2026-07-20 08:00', NULL),
    (2, 1, '2026-07-10 09:00', '2026-07-15 14:00'),
    (5, 3, '2026-06-01 10:00', NULL),
    (5, 1, '2026-07-25 08:00', '2026-07-28 16:00');


-- --------------------------------------------
-- vw_pacientes_internados
-- --------------------------------------------
-- Pacientes cuja internação mais recente está com data_hora_saida IS NULL.
CREATE OR REPLACE VIEW vw_pacientes_internados AS
SELECT ps.id_pessoa AS id_paciente,
       ps.nome,
       ps.cpf,
       u.id_unidade,
       u.nome            AS unidade,
       ui.data_hora_entrada
  FROM (
        SELECT i.*,
               ROW_NUMBER() OVER (PARTITION BY id_paciente ORDER BY data_hora_entrada DESC) AS rn
          FROM internacao i
       ) ui
  JOIN paciente pac ON pac.id_pessoa = ui.id_paciente
  JOIN pessoa   ps  ON ps.id_pessoa  = pac.id_pessoa
  JOIN unidade  u   ON u.id_unidade  = ui.id_unidade
 WHERE ui.rn = 1
   AND ui.data_hora_saida IS NULL
 ORDER BY ui.data_hora_entrada;


-- vw_residentes_sem_supervisor

-- Uma linha por plantão irregular (motivo 'Preceptor sem doutorado'), mais uma linha
-- por residente sem nenhuma escala (motivo 'Sem plantão atribuído', colunas NULL).
--
-- DECISÃO: "tem titulação de doutor" = Doutor, Pos-Doutor e Livre-Docente (as duas
-- últimas pressupõem doutorado). Irregular, então, é só Especialista e Mestre.
CREATE OR REPLACE VIEW vw_residentes_sem_supervisor AS
SELECT res_ps.id_pessoa       AS id_residente,
       res_ps.nome            AS residente,
       r.ano_residencia,
       'Preceptor sem doutorado'::VARCHAR AS motivo,
       e.id_escala,
       u.nome                 AS unidade,
       e.dia_semana,
       e.turno,
       prec_ps.id_pessoa      AS id_preceptor,
       prec_ps.nome           AS preceptor,
       prec.titulacao         AS titulacao_preceptor
  FROM escala e
  JOIN residente    r       ON r.id_profissional     = e.id_residente
  JOIN profissional res_pf  ON res_pf.id_pessoa      = r.id_profissional
  JOIN pessoa       res_ps  ON res_ps.id_pessoa      = res_pf.id_pessoa
  JOIN preceptor    prec    ON prec.id_profissional  = e.id_preceptor
  JOIN profissional prec_pf ON prec_pf.id_pessoa     = prec.id_profissional
  JOIN pessoa       prec_ps ON prec_ps.id_pessoa     = prec_pf.id_pessoa
  JOIN unidade      u       ON u.id_unidade          = e.id_unidade
 WHERE prec.titulacao NOT IN ('Doutor', 'Pos-Doutor', 'Livre-Docente')

UNION ALL

SELECT res_ps.id_pessoa,
       res_ps.nome,
       r.ano_residencia,
       'Sem plantão atribuído'::VARCHAR,
       NULL, NULL, NULL, NULL, NULL, NULL, NULL
  FROM residente    r
  JOIN profissional res_pf ON res_pf.id_pessoa = r.id_profissional
  JOIN pessoa       res_ps ON res_ps.id_pessoa = res_pf.id_pessoa
 WHERE NOT EXISTS (
        SELECT 1 FROM escala e WHERE e.id_residente = r.id_profissional
       )

 ORDER BY motivo, residente, dia_semana, turno;


-- vw_estatisticas_atendimentos_mensal

-- No-op na prática: a coluna já vem de sql/05_procedures.sql (lá com FK e índice).
-- Fica aqui só para a view não depender da ordem de execução dos arquivos.
ALTER TABLE atendimento
    ADD COLUMN IF NOT EXISTS id_unidade INTEGER;

-- Total, média de duração e os 3 procedimentos mais comuns por mês e unidade. Comuns
-- = em mais atendimentos (não soma de quantidade), com desempate por id_procedimento.
--
-- Atendimento com id_unidade NULL entra como "(sem unidade informada)" em vez de
-- sumir do relatório — a sp_registrar_atendimento_completo ainda não preenche a coluna.
CREATE OR REPLACE VIEW vw_estatisticas_atendimentos_mensal AS
WITH atendimento_mes AS (
    SELECT DATE_TRUNC('month', a.data_hora)::DATE AS mes,
           a.id_unidade,
           a.id_atendimento,
           a.duracao_minutos
      FROM atendimento a
),
procedimento_contagem AS (
    SELECT am.mes,
           am.id_unidade,
           pr.id_procedimento,
           COUNT(DISTINCT pr.id_atendimento) AS vezes,
           ROW_NUMBER() OVER (
               PARTITION BY am.mes, am.id_unidade
               ORDER BY COUNT(DISTINCT pr.id_atendimento) DESC, pr.id_procedimento
           ) AS posicao
      FROM atendimento_mes am
      JOIN procedimento_realizado pr ON pr.id_atendimento = am.id_atendimento
     GROUP BY am.mes, am.id_unidade, pr.id_procedimento
),
procedimentos_top AS (
    SELECT pc.mes,
           pc.id_unidade,
           STRING_AGG(p.nome || ' (' || pc.vezes || 'x)', ', ' ORDER BY pc.posicao)
               AS procedimentos_mais_comuns
      FROM procedimento_contagem pc
      JOIN procedimento p ON p.id_procedimento = pc.id_procedimento
     WHERE pc.posicao <= 3
     GROUP BY pc.mes, pc.id_unidade
)
SELECT am.mes,
       TO_CHAR(am.mes, 'MM/YYYY')                       AS mes_referencia,
       am.id_unidade,
       COALESCE(u.nome, '(sem unidade informada)')      AS unidade,
       COUNT(*)                                         AS total_atendimentos,
       ROUND(AVG(am.duracao_minutos), 2)                AS media_duracao_minutos,
       MIN(am.duracao_minutos)                          AS menor_duracao_minutos,
       MAX(am.duracao_minutos)                          AS maior_duracao_minutos,
       pt.procedimentos_mais_comuns
  FROM atendimento_mes am
  LEFT JOIN unidade u
         ON u.id_unidade = am.id_unidade
  LEFT JOIN procedimentos_top pt
         ON pt.mes = am.mes
        AND pt.id_unidade IS NOT DISTINCT FROM am.id_unidade
 GROUP BY am.mes, am.id_unidade, u.nome, pt.procedimentos_mais_comuns
 ORDER BY am.mes DESC, unidade;
