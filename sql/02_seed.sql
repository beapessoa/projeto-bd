BEGIN;

TRUNCATE TABLE
    pessoa, profissional, paciente, preceptor, residente,
    alergia, paciente_alergia, unidade, procedimento,
    atendimento, procedimento_realizado, escala
RESTART IDENTITY CASCADE;

INSERT INTO pessoa (id_pessoa, nome, cpf, data_nascimento, is_flamengo, telefone) VALUES
    ( 1, 'Maria Silva',        '10000000001', '1990-03-12', TRUE,  '(83) 98800-0001'),
    ( 2, 'João Souza',         '20000000002', '1985-07-25', FALSE, '(83) 98800-0002'),
    ( 3, 'Ana Pereira',        '30000000003', '2001-11-05', TRUE,  '(83) 98800-0003'),
    ( 4, 'Carlos Lima',        '40000000004', '1970-01-30', FALSE, '(83) 98800-0004'),
    ( 5, 'Beatriz Costa',      '50000000005', '1995-09-18', TRUE,  '(83) 98800-0005'),
    ( 6, 'Dr. Ricardo Alves',  '60000000006', '1968-02-14', FALSE, '(83) 98800-0006'),
    ( 7, 'Dra. Fernanda Rocha','70000000007', '1972-06-09', TRUE,  '(83) 98800-0007'),
    ( 8, 'Dr. Paulo Mendes',   '80000000008', '1965-12-01', FALSE, '(83) 98800-0008'),
    ( 9, 'Dra. Juliana Dias',  '90000000009', '1975-04-22', TRUE,  '(83) 98800-0009'),
    (10, 'Dr. Marcos Teixeira','11000000010', '1970-08-17', FALSE, '(83) 98800-0010'),
    (11, 'Rafael Nunes',       '12000000011', '1996-05-03', TRUE,  '(83) 98800-0011'),
    (12, 'Camila Freitas',     '13000000012', '1997-10-19', FALSE, '(83) 98800-0012'),
    (13, 'Lucas Barros',       '14000000013', '1998-01-27', TRUE,  '(83) 98800-0013'),
    (14, 'Patrícia Gomes',     '15000000014', '1995-12-08', FALSE, '(83) 98800-0014'),
    (15, 'Thiago Ramos',       '16000000015', '1999-03-15', TRUE,  '(83) 98800-0015');

INSERT INTO profissional (id_pessoa, crm, data_admissao, especialidade) VALUES
    ( 6, 'CRM-PB 10001', '2005-02-01', 'Cardiologia'),
    ( 7, 'CRM-PB 10002', '2008-03-15', 'Pediatria'),
    ( 8, 'CRM-PB 10003', '2001-08-20', 'Cirurgia Geral'),
    ( 9, 'CRM-PB 10004', '2010-05-10', 'Clínica Médica'),
    (10, 'CRM-PB 10005', '2006-11-30', 'Ortopedia'),
    (11, 'CRM-PB 20001', '2023-02-01', 'Clínica Médica'),
    (12, 'CRM-PB 20002', '2023-02-01', 'Pediatria'),
    (13, 'CRM-PB 20003', '2024-02-01', 'Cirurgia Geral'),
    (14, 'CRM-PB 20004', '2022-02-01', 'Cardiologia'),
    (15, 'CRM-PB 20005', '2024-02-01', 'Ortopedia');

INSERT INTO paciente (id_pessoa, num_convenio, grupo_sanguineo) VALUES
    (1, 'UNIMED-0001', 'O+'),
    (2, 'HAPVIDA-0002','A-'),
    (3, NULL,          'B+'),
    (4, 'BRADESCO-004','AB+'),
    (5, NULL,          'O-');

INSERT INTO preceptor (id_profissional, titulacao) VALUES
    ( 6, 'Doutor'),
    ( 7, 'Mestre'),
    ( 8, 'Livre-Docente'),
    ( 9, 'Doutor'),
    (10, 'Especialista');

INSERT INTO residente (id_profissional, ano_residencia) VALUES
    (11, 'R2'),
    (12, 'R2'),
    (13, 'R1'),
    (14, 'R3'),
    (15, 'R1');

INSERT INTO alergia (id_alergia, nome) VALUES
    (1, 'Dipirona'),
    (2, 'Penicilina'),
    (3, 'Látex'),
    (4, 'Ácido Acetilsalicílico'),
    (5, 'Iodo');

INSERT INTO paciente_alergia (id_paciente, id_alergia) VALUES
    (1, 1),
    (1, 2),
    (2, 3),
    (4, 5),
    (5, 4);

INSERT INTO unidade (id_unidade, nome, tipo, capacidade_leitos) VALUES
    (1, 'Enfermaria A',                 'Enfermaria',     20),
    (2, 'UTI Geral',                    'UTI',            10),
    (3, 'Pronto-Socorro Central',       'Pronto-Socorro', 15),
    (4, 'Ambulatório de Especialidades','Ambulatorio',     0);

INSERT INTO procedimento (id_procedimento, codigo, nome, tempo_medio_minutos) VALUES
    (1, 'SUT001', 'Sutura simples',         30),
    (2, 'COL001', 'Coleta de sangue',       15),
    (3, 'MED001', 'Aplicação de medicação', 10),
    (4, 'CUR001', 'Curativo',               20),
    (5, 'GES001', 'Gesso / imobilização',   40),
    (6, 'PUN001', 'Punção venosa',          12),
    (7, 'ECG001', 'Eletrocardiograma',      15),
    (8, 'NEB001', 'Nebulização',            25);

INSERT INTO atendimento (id_atendimento, data_hora, duracao_minutos, id_paciente, id_residente, id_preceptor) VALUES
    ( 1, '2026-07-01 08:00', 30, 1, 11,  6),
    ( 2, '2026-07-02 09:00', 45, 2, 11,  6),
    ( 3, '2026-07-03 10:00', 20, 3, 12,  6),
    ( 4, '2026-07-05 14:00', 60, 4, 11,  6),
    ( 5, '2026-07-08 11:00', 25, 5, 12,  6),
    ( 6, '2026-07-10 15:00', 35, 1, 11,  6),
    ( 7, '2026-07-04 08:30', 40, 2, 13,  7),
    ( 8, '2026-06-20 09:00', 30, 3, 13,  7),
    ( 9, '2026-07-06 16:00', 50, 4, 14,  8),
    (10, '2026-06-25 10:00', 20, 5, 14,  8),
    (11, '2026-07-09 13:00', 30, 1, 15,  9),
    (12, '2026-07-11 08:00', 45, 2, 15,  9),
    (13, '2026-06-28 14:00', 25, 3, 12, 10),
    (14, '2026-07-12 09:30', 40, 5, 13, 10);

INSERT INTO procedimento_realizado
    (id_atendimento, id_procedimento, quantidade, tempo_real_minutos, observacao) VALUES
    ( 1, 1, 1, 35, 'Sutura em MSD, sem intercorrências'),
    ( 1, 2, 1, 12, 'Coleta para hemograma'),
    ( 2, 3, 2, 15, 'Dipirona endovenosa'),
    ( 2, 6, 1, 10, 'Punção em MSE'),
    ( 3, 4, 1, 18, 'Curativo em ferida operatória'),
    ( 4, 5, 1, 55, 'Imobilização de tornozelo'),
    ( 5, 8, 3, 30, 'Nebulização com salbutamol'),
    ( 6, 2, 1, 14, 'Coleta de rotina'),
    ( 7, 7, 1, 15, 'ECG sem alterações'),
    ( 8, 3, 1,  8, 'Analgésico via oral'),
    ( 9, 1, 2, 48, 'Duas suturas em face'),
    (10, 4, 1, 20, 'Troca de curativo'),
    (11, 6, 1, 12, 'Acesso venoso periférico'),
    (12, 7, 1, 16, 'ECG de controle'),
    (13, 8, 2, 25, 'Nebulização'),
    (14, 5, 1, 42, 'Imobilização de punho');

INSERT INTO escala (id_unidade, dia_semana, turno, id_residente, id_preceptor) VALUES
    (3, 'Segunda', 'Manha', 11,  6),
    (3, 'Segunda', 'Manha', 12,  6),
    (2, 'Segunda', 'Tarde', 11,  7),
    (1, 'Terca',   'Noite', 13,  8),
    (3, 'Quarta',  'Manha', 14,  9),
    (4, 'Quinta',  'Tarde', 15, 10),
    (2, 'Sexta',   'Noite', 12,  7),
    (1, 'Sabado',  'Manha', 13,  6),
    (3, 'Domingo', 'Tarde', 14,  8),
    (4, 'Sexta',   'Manha', 15,  9);

SELECT setval('pessoa_id_pessoa_seq',           (SELECT MAX(id_pessoa)      FROM pessoa));
SELECT setval('unidade_id_unidade_seq',         (SELECT MAX(id_unidade)     FROM unidade));
SELECT setval('procedimento_id_procedimento_seq',(SELECT MAX(id_procedimento) FROM procedimento));
SELECT setval('alergia_id_alergia_seq',         (SELECT MAX(id_alergia)     FROM alergia));
SELECT setval('atendimento_id_atendimento_seq', (SELECT MAX(id_atendimento) FROM atendimento));

COMMIT;
