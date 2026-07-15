DROP TABLE IF EXISTS
    paciente_alergia,
    procedimento_realizado,
    escala,
    atendimento,
    residente,
    preceptor,
    profissional,
    paciente,
    alergia,
    procedimento,
    unidade,
    pessoa
CASCADE;


CREATE TABLE pessoa (
    id_pessoa       SERIAL       PRIMARY KEY,
    nome            VARCHAR(120) NOT NULL,
    cpf             CHAR(11)     NOT NULL,
    data_nascimento DATE         NOT NULL,
    is_flamengo     BOOLEAN      NOT NULL DEFAULT FALSE,
    telefone        VARCHAR(20)  NOT NULL,
    endereco        VARCHAR(150),

    CONSTRAINT uq_pessoa_cpf
        UNIQUE (cpf),

    CONSTRAINT ck_pessoa_cpf
        CHECK (cpf ~ '^[0-9]{11}$'),

    CONSTRAINT ck_pessoa_nome
        CHECK (TRIM(nome) <> ''),

    CONSTRAINT ck_pessoa_data_nascimento
        CHECK (data_nascimento <= CURRENT_DATE)
);

CREATE TABLE profissional (
    id_pessoa     INTEGER      PRIMARY KEY,
    crm           VARCHAR(20)  NOT NULL,
    data_admissao DATE         NOT NULL,
    especialidade VARCHAR(80)  NOT NULL,

    CONSTRAINT uq_profissional_crm
        UNIQUE (crm),

    CONSTRAINT fk_profissional_pessoa
        FOREIGN KEY (id_pessoa) REFERENCES pessoa (id_pessoa)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    CONSTRAINT ck_profissional_data_admissao
        CHECK (data_admissao <= CURRENT_DATE),

    CONSTRAINT ck_profissional_especialidade
        CHECK (TRIM(especialidade) <> ''),
);

CREATE TABLE paciente (
    id_pessoa       INTEGER     PRIMARY KEY,
    num_convenio    VARCHAR(30),
    grupo_sanguineo VARCHAR(3)  NOT NULL,

    CONSTRAINT fk_paciente_pessoa
        FOREIGN KEY (id_pessoa) REFERENCES pessoa (id_pessoa)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    CONSTRAINT ck_paciente_grupo_sanguineo
        CHECK (grupo_sanguineo IN ('A+','A-','B+','B-','AB+','AB-','O+','O-'))
);

CREATE TABLE preceptor (
    id_profissional INTEGER     PRIMARY KEY,
    titulacao       VARCHAR(30) NOT NULL,

    CONSTRAINT fk_preceptor_profissional
        FOREIGN KEY (id_profissional) REFERENCES profissional (id_pessoa)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    CONSTRAINT ck_preceptor_titulacao
        CHECK (titulacao IN ('Especialista','Mestre','Doutor','Pos-Doutor','Livre-Docente'))
);

CREATE TABLE residente (
    id_profissional INTEGER    PRIMARY KEY,
    ano_residencia  VARCHAR(2) NOT NULL,

    CONSTRAINT fk_residente_profissional
        FOREIGN KEY (id_profissional) REFERENCES profissional (id_pessoa)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    CONSTRAINT ck_residente_ano
        CHECK (ano_residencia IN ('R1','R2','R3'))
);

CREATE TABLE alergia (
    id_alergia SERIAL      PRIMARY KEY,
    nome       VARCHAR(80) NOT NULL,

    CONSTRAINT uq_alergia_nome
        UNIQUE (nome),

    CONSTRAINT ck_alergia_nome
        CHECK (TRIM(nome) <> ''),
);

CREATE TABLE paciente_alergia (
    id_paciente INTEGER NOT NULL,
    id_alergia  INTEGER NOT NULL,

    CONSTRAINT pk_paciente_alergia
        PRIMARY KEY (id_paciente, id_alergia),

    CONSTRAINT fk_pac_alergia_paciente
        FOREIGN KEY (id_paciente) REFERENCES paciente (id_pessoa)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    CONSTRAINT fk_pac_alergia_alergia
        FOREIGN KEY (id_alergia) REFERENCES alergia (id_alergia)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);


CREATE TABLE unidade (
    id_unidade        SERIAL      PRIMARY KEY,
    nome              VARCHAR(80) NOT NULL,
    tipo              VARCHAR(20) NOT NULL,
    capacidade_leitos INTEGER     NOT NULL,

    CONSTRAINT uq_unidade_nome
        UNIQUE (nome),

    CONSTRAINT ck_unidade_tipo
        CHECK (tipo IN ('Enfermaria','UTI','Pronto-Socorro','Ambulatorio')),

    CONSTRAINT ck_unidade_leitos
        CHECK (capacidade_leitos >= 0)
);


CREATE TABLE procedimento (
    id_procedimento     SERIAL       PRIMARY KEY,
    codigo              VARCHAR(20)  NOT NULL,
    nome                VARCHAR(120) NOT NULL,
    tempo_medio_minutos INTEGER      NOT NULL,
    nivel_risco         VARCHAR(5)   NOT NULL DEFAULT 'BAIXO',

    CONSTRAINT uq_procedimento_codigo
        UNIQUE (codigo),

    CONSTRAINT ck_procedimento_nome
        CHECK (TRIM(nome) <> ''),

    CONSTRAINT ck_procedimento_tempo_medio
        CHECK (tempo_medio_minutos > 0),

    CONSTRAINT ck_procedimento_nivel_risco
        CHECK (nivel_risco IN ('BAIXO','MEDIO','ALTO'))
);

CREATE TABLE atendimento (
    id_atendimento  SERIAL    PRIMARY KEY,
    data_hora       TIMESTAMP NOT NULL,
    duracao_minutos INTEGER   NOT NULL,
    id_paciente     INTEGER   NOT NULL,
    id_residente    INTEGER   NOT NULL,
    id_preceptor    INTEGER   NOT NULL,

    CONSTRAINT fk_atendimento_paciente
        FOREIGN KEY (id_paciente)  REFERENCES paciente  (id_pessoa)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT fk_atendimento_residente
        FOREIGN KEY (id_residente) REFERENCES residente (id_profissional)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT fk_atendimento_preceptor
        FOREIGN KEY (id_preceptor) REFERENCES preceptor (id_profissional)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT ck_atendimento_duracao
        CHECK (duracao_minutos > 0)
);

CREATE TABLE procedimento_realizado (
    id_atendimento      INTEGER NOT NULL,
    id_procedimento     INTEGER NOT NULL,
    quantidade          INTEGER NOT NULL,
    tempo_real_minutos  INTEGER NOT NULL,
    observacao          TEXT,
    faturado            BOOLEAN NOT NULL DEFAULT FALSE,

    CONSTRAINT pk_procedimento_realizado
        PRIMARY KEY (id_atendimento, id_procedimento),

    CONSTRAINT fk_proc_real_atendimento
        FOREIGN KEY (id_atendimento)  REFERENCES atendimento  (id_atendimento)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    CONSTRAINT fk_proc_real_procedimento
        FOREIGN KEY (id_procedimento) REFERENCES procedimento (id_procedimento)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CONSTRAINT ck_proc_real_quantidade
        CHECK (quantidade > 0),

    CONSTRAINT ck_proc_real_tempo_real
        CHECK (tempo_real_minutos > 0)
);

CREATE TABLE escala (
    id_escala    SERIAL      PRIMARY KEY,
    id_unidade   INTEGER     NOT NULL,
    dia_semana   VARCHAR(10) NOT NULL,
    turno        VARCHAR(10) NOT NULL,
    id_residente INTEGER     NOT NULL,
    id_preceptor INTEGER     NOT NULL,

    CONSTRAINT fk_escala_unidade
        FOREIGN KEY (id_unidade)   REFERENCES unidade   (id_unidade)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    CONSTRAINT fk_escala_residente
        FOREIGN KEY (id_residente) REFERENCES residente (id_profissional)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    CONSTRAINT fk_escala_preceptor
        FOREIGN KEY (id_preceptor) REFERENCES preceptor (id_profissional)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    CONSTRAINT ck_escala_dia_semana
        CHECK (dia_semana IN ('Segunda','Terca','Quarta','Quinta','Sexta','Sabado','Domingo')),

    CONSTRAINT ck_escala_turno
        CHECK (turno IN ('Manha','Tarde','Noite')),

    CONSTRAINT uq_escala_plantao
        UNIQUE (id_unidade, dia_semana, turno, id_residente)
);

CREATE INDEX idx_atendimento_paciente     ON atendimento (id_paciente);
CREATE INDEX idx_atendimento_residente    ON atendimento (id_residente);
CREATE INDEX idx_atendimento_preceptor    ON atendimento (id_preceptor);
CREATE INDEX idx_proc_real_procedimento   ON procedimento_realizado (id_procedimento);
CREATE INDEX idx_escala_unidade           ON escala (id_unidade);
CREATE INDEX idx_escala_residente         ON escala (id_residente);
CREATE INDEX idx_escala_preceptor         ON escala (id_preceptor);
CREATE INDEX idx_paciente_alergia_alergia ON paciente_alergia (id_alergia);