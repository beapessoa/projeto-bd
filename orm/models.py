"""
Mapeamento objeto-relacional das tabelas do hospital (Etapa 2, requisito 4).

Espelha o schema criado em sql/01_schema.sql — os models NÃO criam tabelas,
apenas mapeiam as que já existem.

Sobre a especialização PESSOA -> PACIENTE / PROFISSIONAL -> PRECEPTOR / RESIDENTE:
o schema da Etapa 1 usa FK-como-PK, mas não tem coluna discriminadora (algo como
"tipo_pessoa"). A herança de tabelas do SQLAlchemy (joined table inheritance)
depende dessa coluna para saber qual subclasse instanciar ao carregar uma linha.
Como adicioná-la mudaria o schema entregue na Etapa 1 sem necessidade, a
especialização foi mapeada por COMPOSIÇÃO: cada subtipo tem um relationship 1:1
com o supertipo (ex.: Paciente.pessoa), em vez de herdar dele.
"""
from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text,
)
from sqlalchemy.orm import relationship

from orm.db import Base


class Pessoa(Base):
    __tablename__ = "pessoa"

    id_pessoa = Column(Integer, primary_key=True)
    nome = Column(String(120), nullable=False)
    cpf = Column(String(11), nullable=False, unique=True)
    data_nascimento = Column(Date, nullable=False)
    is_flamengo = Column(Boolean, nullable=False, default=False)
    telefone = Column(String(20), nullable=False)
    endereco = Column(String(150))

    # lazy (padrão "select"): partindo de Pessoa quase nunca precisamos do subtipo
    # — as telas sempre entram pelo subtipo (lista de pacientes, de residentes...).
    paciente = relationship("Paciente", back_populates="pessoa", uselist=False)
    profissional = relationship("Profissional", back_populates="pessoa", uselist=False)


class Profissional(Base):
    __tablename__ = "profissional"

    id_pessoa = Column(Integer, ForeignKey("pessoa.id_pessoa"), primary_key=True)
    crm = Column(String(20), nullable=False, unique=True)
    data_admissao = Column(Date, nullable=False)
    especialidade = Column(String(80), nullable=False)

    # eager: nenhum dado de profissional é exibido sem o nome/CPF da pessoa junto.
    # Com lazy daria N+1 (uma query extra por linha) em toda listagem.
    pessoa = relationship("Pessoa", back_populates="profissional", lazy="joined")

    preceptor = relationship("Preceptor", back_populates="profissional", uselist=False)
    residente = relationship("Residente", back_populates="profissional", uselist=False)


class Paciente(Base):
    __tablename__ = "paciente"

    id_pessoa = Column(Integer, ForeignKey("pessoa.id_pessoa"), primary_key=True)
    num_convenio = Column(String(30))
    grupo_sanguineo = Column(String(3), nullable=False)

    # eager, mesmo motivo do Profissional.pessoa.
    pessoa = relationship("Pessoa", back_populates="paciente", lazy="joined")

    # selectin (eager, mas em uma segunda query): a listagem de pacientes mostra as
    # alergias de todos. Com "joined" o JOIN da coleção multiplicaria as linhas do
    # paciente (uma por alergia); com lazy seria N+1. "selectin" resolve as duas
    # coisas: uma query para os pacientes e outra só para as alergias deles.
    alergias = relationship(
        "Alergia",
        secondary="paciente_alergia",
        back_populates="pacientes",
        lazy="selectin",
        order_by="Alergia.nome",
    )


class Preceptor(Base):
    __tablename__ = "preceptor"

    id_profissional = Column(Integer, ForeignKey("profissional.id_pessoa"), primary_key=True)
    titulacao = Column(String(30), nullable=False)

    # eager: um preceptor nunca é exibido sem CRM/especialidade (e, via Profissional,
    # sem o nome da pessoa) — o encadeamento carrega preceptor -> profissional -> pessoa
    # em um único SELECT.
    profissional = relationship("Profissional", back_populates="preceptor", lazy="joined")

    @property
    def pessoa(self):
        return self.profissional.pessoa


class Residente(Base):
    __tablename__ = "residente"

    id_profissional = Column(Integer, ForeignKey("profissional.id_pessoa"), primary_key=True)
    ano_residencia = Column(String(2), nullable=False)

    # eager, mesmo motivo do Preceptor.profissional.
    profissional = relationship("Profissional", back_populates="residente", lazy="joined")

    @property
    def pessoa(self):
        return self.profissional.pessoa


class Alergia(Base):
    __tablename__ = "alergia"

    id_alergia = Column(Integer, primary_key=True)
    nome = Column(String(80), nullable=False, unique=True)

    # lazy: partindo de uma alergia, listar todos os pacientes que a têm não é usado
    # em nenhuma tela — só carrega se alguém pedir explicitamente.
    pacientes = relationship("Paciente", secondary="paciente_alergia", back_populates="alergias")


class PacienteAlergia(Base):
    """
    Tabela associativa do N:N paciente <-> alergia.

    Mapeada como classe (e não só como Table) porque o enunciado pede a entidade,
    e porque permite inserir/remover vínculos explicitamente. O relationship
    Paciente.alergias usa esta mesma tabela como `secondary`.
    """

    __tablename__ = "paciente_alergia"

    id_paciente = Column(Integer, ForeignKey("paciente.id_pessoa"), primary_key=True)
    id_alergia = Column(Integer, ForeignKey("alergia.id_alergia"), primary_key=True)


class Unidade(Base):
    __tablename__ = "unidade"

    id_unidade = Column(Integer, primary_key=True)
    nome = Column(String(80), nullable=False, unique=True)
    tipo = Column(String(20), nullable=False)
    capacidade_leitos = Column(Integer, nullable=False)

    # lazy: a tela de unidades mostra só os dados da unidade; as escalas são
    # consultadas pela própria tela de escalas, com seus filtros.
    escalas = relationship("Escala", back_populates="unidade")


class Escala(Base):
    __tablename__ = "escala"

    id_escala = Column(Integer, primary_key=True)
    id_unidade = Column(Integer, ForeignKey("unidade.id_unidade"), nullable=False)
    dia_semana = Column(String(10), nullable=False)
    turno = Column(String(10), nullable=False)
    id_residente = Column(Integer, ForeignKey("residente.id_profissional"), nullable=False)
    id_preceptor = Column(Integer, ForeignKey("preceptor.id_profissional"), nullable=False)
    version_id = Column(Integer, nullable=False, default=1)

    __mapper_args__ = {"version_id_col": version_id}

    # Os três eager: a listagem de escalas exibe, em cada linha, o nome da unidade,
    # do residente e do preceptor. Com lazy seriam 3 queries extras por escala.
    unidade = relationship("Unidade", back_populates="escalas", lazy="joined")
    residente = relationship("Residente", lazy="joined")
    preceptor = relationship("Preceptor", lazy="joined")


class Procedimento(Base):
    __tablename__ = "procedimento"

    id_procedimento = Column(Integer, primary_key=True)
    codigo = Column(String(20), nullable=False, unique=True)
    nome = Column(String(120), nullable=False)
    tempo_medio_minutos = Column(Integer, nullable=False)
    nivel_risco = Column(String(5), nullable=False, default="BAIXO")

    # Só de leitura no app: quem mantém é o trigger trg_atualiza_media_procedimentos.
    media_tempo_procedimento = Column(Numeric(10, 2))

    # lazy: o catálogo de procedimentos é listado sozinho; ninguém parte de um
    # procedimento para ver todas as vezes que ele foi realizado.
    realizacoes = relationship("ProcedimentoRealizado", back_populates="procedimento")


class Atendimento(Base):
    __tablename__ = "atendimento"

    id_atendimento = Column(Integer, primary_key=True)
    data_hora = Column(DateTime, nullable=False)
    duracao_minutos = Column(Integer, nullable=False)
    id_paciente = Column(Integer, ForeignKey("paciente.id_pessoa"), nullable=False)
    id_residente = Column(Integer, ForeignKey("residente.id_profissional"), nullable=False)
    id_preceptor = Column(Integer, ForeignKey("preceptor.id_profissional"), nullable=False)

    # Nullable: coluna acrescentada na Etapa 2 (sql/05_procedures.sql), os
    # atendimentos da Etapa 1 não tinham unidade.
    id_unidade = Column(Integer, ForeignKey("unidade.id_unidade"))

    # Os três eager: toda listagem de atendimento mostra os nomes de paciente,residente e preceptor.
    paciente = relationship("Paciente", lazy="joined")
    residente = relationship("Residente", lazy="joined")
    preceptor = relationship("Preceptor", lazy="joined")

    # lazy: a unidade não aparece em nenhuma listagem de atendimento hoje.
    unidade = relationship("Unidade")

    # lazy: os procedimentos têm tela própria (modal), carregada sob demanda
    procedimentos = relationship(
        "ProcedimentoRealizado",
        back_populates="atendimento",
        cascade="all, delete-orphan",
    )


class ProcedimentoRealizado(Base):
    """Associativa N:N atendimento <-> procedimento, com atributos próprios."""

    __tablename__ = "procedimento_realizado"

    id_atendimento = Column(Integer, ForeignKey("atendimento.id_atendimento"), primary_key=True)
    id_procedimento = Column(Integer, ForeignKey("procedimento.id_procedimento"), primary_key=True)
    quantidade = Column(Integer, nullable=False)
    tempo_real_minutos = Column(Integer, nullable=False)
    observacao = Column(Text)
    faturado = Column(Boolean, nullable=False, default=False)

    # Quando o procedimento começou, usada por sp_calcular_tempo_medio_espera.
    hora_inicio = Column(DateTime)

    atendimento = relationship("Atendimento", back_populates="procedimentos")

    # eager: a listagem de procedimentos de um atendimento mostra código, nome e
    # nível de risco — sem isso seria uma query extra por linha.
    procedimento = relationship("Procedimento", back_populates="realizacoes", lazy="joined")
