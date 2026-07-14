-- ============================================
-- Hospital Universitário Dra. Yuska Maritan Brito
-- Script de criação do banco de dados
-- ============================================

-- PESSOA (id_pessoa PK, nome, CPF, data_nascimento, is_flamengo, telefone)
-- TODO

-- PACIENTE (id_pessoa PK/FK → PESSOA, num_convenio, alergias, grupo_sanguineo)
-- TODO

-- PROFISSIONAL (id_pessoa PK/FK → PESSOA, CRM, data_admissao, especialidade)
-- TODO

-- PRECEPTOR (id_profissional PK/FK → PROFISSIONAL, titulacao)
-- TODO

-- RESIDENTE (id_profissional PK/FK → PROFISSIONAL, ano_residencia)
-- TODO

-- UNIDADE (id_unidade PK, nome, tipo, capacidade_leitos)
-- TODO

-- ATENDIMENTO (id_atendimento PK, data_hora, duracao_minutos, id_paciente FK, id_residente FK, id_preceptor FK)
-- TODO

-- PROCEDIMENTO (id_procedimento PK, codigo, nome, tempo_medio_minutos)
-- TODO

-- PROCEDIMENTO_REALIZADO (id_atendimento FK, id_procedimento FK, quantidade, tempo_real_minutos, observacao, PK composta)
-- TODO

-- ESCALA (id_escala PK, id_unidade FK, dia_semana, turno, id_residente FK, id_preceptor FK, UNIQUE)
-- TODO
