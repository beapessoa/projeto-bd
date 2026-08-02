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
