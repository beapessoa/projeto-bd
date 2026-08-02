"""
Servidor do Hospital Dra. Yuska Maritan Brito.

Etapa 1: Flask + psycopg2 (SQL puro).
Etapa 2: os cadastros (pacientes, profissionais, unidades, escalas) e a consulta
analítica 4.3 foram migrados para SQLAlchemy — ver orm/models.py e orm/db.py.

Rodar:  python app.py   ->   http://localhost:8000
Config do banco via variáveis de ambiente (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD).
"""
import os
import calendar
import getpass
from datetime import date

import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, request
from sqlalchemy import case, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import contains_eager

from orm.db import SessionLocal
from orm.models import (
    Alergia, Escala, Paciente, PacienteAlergia, Pessoa, Preceptor, Profissional,
    Residente, Unidade,
)

app = Flask(__name__, static_folder="frontend", static_url_path="")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
    "dbname": os.getenv("DB_NAME", "hospital_yuska"),
    "user": os.getenv("DB_USER", getpass.getuser()),
    "password": os.getenv("DB_PASSWORD", ""),
}


def get_conn():
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)


def query(sql, params=None):
    """Executa um SELECT e devolve a lista de linhas (dicts)."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        conn.close()


def escrever(fn):
    """
    Roda fn(sessao) numa transação do SQLAlchemy: commit no fim, rollback se falhar.
    Devolve (resultado, None) ou (None, mensagem_erro).
    """
    s = SessionLocal()
    try:
        result = fn(s)
        s.commit()
        return result, None
    except SQLAlchemyError as exc:
        s.rollback()
        return None, amigavel(str(getattr(exc, "orig", exc)))
    except ValueError as exc:
        s.rollback()
        return None, str(exc)
    finally:
        s.close()


def data_iso(valor, campo):
    """Converte 'YYYY-MM-DD' em date, com mensagem de erro legível."""
    try:
        return date.fromisoformat(valor)
    except (TypeError, ValueError):
        raise ValueError(f"Campo {campo} deve estar no formato AAAA-MM-DD.")


def inteiro(valor, campo):
    try:
        return int(valor)
    except (TypeError, ValueError):
        raise ValueError(f"Campo {campo} deve ser um número inteiro.")


def body():
    return request.get_json(silent=True) or {}


def obrigatorios(d, campos):
    faltam = [c for c in campos if d.get(c) in (None, "")]
    return f"Campos obrigatórios: {', '.join(faltam)}" if faltam else None


def amigavel(msg):
    """Traduz erros comuns de constraint para mensagens legíveis."""
    mapa = {
        "uq_pessoa_cpf": "Já existe uma pessoa com esse CPF.",
        "uq_profissional_crm": "Já existe um profissional com esse CRM.",
        "uq_unidade_nome": "Já existe uma unidade com esse nome.",
        "uq_escala_plantao": "Já existe uma escala para esse residente nessa unidade/dia/turno.",
        "ck_pessoa_cpf": "CPF deve ter exatamente 11 dígitos numéricos.",
        "ck_paciente_grupo_sanguineo": "Grupo sanguíneo inválido.",
        "ck_unidade_tipo": "Tipo de unidade inválido.",
    }
    for chave, texto in mapa.items():
        if chave in (msg or ""):
            return texto
    return msg


def inserir_pessoa(s, d):
    """Cria a PESSOA (supertipo) via ORM e devolve o objeto já com id."""
    pessoa = Pessoa(
        nome=d["nome"],
        cpf=d["cpf"],
        data_nascimento=data_iso(d["data_nascimento"], "data_nascimento"),
        telefone=d["telefone"],
        endereco=d.get("endereco") or None,
        is_flamengo=bool(d.get("is_flamengo", False)),
    )
    s.add(pessoa)
    s.flush()  # força o INSERT agora para obter o id_pessoa gerado
    return pessoa


def inserir_profissional(s, d):
    """Cria PESSOA + PROFISSIONAL (parte comum de residente e preceptor)."""
    pessoa = inserir_pessoa(s, d)
    s.add(Profissional(
        id_pessoa=pessoa.id_pessoa,
        crm=d["crm"],
        data_admissao=data_iso(d["data_admissao"], "data_admissao"),
        especialidade=d["especialidade"],
    ))
    s.flush()
    return pessoa


# ============================================================
# Página
# ============================================================

@app.route("/")
def index():
    return app.send_static_file("index.html")


# ============================================================
# Dashboard
# ============================================================

@app.route("/api/stats")
def stats():
    return jsonify(query(
        """
        SELECT (SELECT count(*) FROM paciente)    AS pacientes,
               (SELECT count(*) FROM residente)   AS residentes,
               (SELECT count(*) FROM preceptor)   AS preceptores,
               (SELECT count(*) FROM atendimento) AS atendimentos
        """
    )[0])


@app.route("/api/atendimentos-recentes")
def atendimentos_recentes():
    return jsonify(query(
        """
        SELECT to_char(a.data_hora, 'DD/MM/YYYY HH24:MI') AS data_hora,
               pac.nome AS paciente, res.nome AS residente,
               prec.nome AS preceptor, a.duracao_minutos
          FROM atendimento a
          JOIN pessoa pac  ON pac.id_pessoa  = a.id_paciente
          JOIN pessoa res  ON res.id_pessoa  = a.id_residente
          JOIN pessoa prec ON prec.id_pessoa = a.id_preceptor
         ORDER BY a.data_hora DESC
         LIMIT 10
        """
    ))


@app.route("/api/tempo-medio-residente")
def tempo_medio_residente():
    # 3.6 — Tempo médio de duração dos atendimentos por residente.
    return jsonify(query(
        """
        SELECT p.nome AS residente,
               COUNT(a.id_atendimento)                  AS qtd_atendimentos,
               ROUND(AVG(a.duracao_minutos), 1)::float8 AS tempo_medio_minutos
          FROM residente r
          JOIN pessoa p      ON p.id_pessoa    = r.id_profissional
          JOIN atendimento a ON a.id_residente = r.id_profissional
         GROUP BY p.id_pessoa, p.nome
         ORDER BY tempo_medio_minutos DESC
        """
    ))


# ============================================================
# Pacientes
# ============================================================

@app.route("/api/pacientes")
def listar_pacientes():
    # Query por entidade: Paciente.pessoa é eager "joined" e Paciente.alergias é
    # eager "selectin", então isso resolve em 2 SELECTs no total (sem N+1).
    s = SessionLocal()
    try:
        pacientes = s.query(Paciente).join(Paciente.pessoa).order_by(Pessoa.nome).all()
        return jsonify([
            {
                "id_pessoa": pac.id_pessoa,
                "nome": pac.pessoa.nome,
                "cpf": pac.pessoa.cpf,
                "endereco": pac.pessoa.endereco,
                "num_convenio": pac.num_convenio,
                "grupo_sanguineo": pac.grupo_sanguineo,
                "alergias": [a.nome for a in pac.alergias],
            }
            for pac in pacientes
        ])
    finally:
        s.close()


def sincronizar_alergias(s, id_paciente, alergias):
    """Reescreve o conjunto de alergias (N:N) do paciente, via ORM."""
    s.query(PacienteAlergia).filter(PacienteAlergia.id_paciente == id_paciente).delete()
    s.flush()

    nomes = {n.strip() for n in alergias if (n or "").strip()}
    for nome in nomes:
        alergia = s.query(Alergia).filter(Alergia.nome == nome).one_or_none()
        if alergia is None:
            alergia = Alergia(nome=nome)
            s.add(alergia)
            s.flush()
        s.add(PacienteAlergia(id_paciente=id_paciente, id_alergia=alergia.id_alergia))
    s.flush()


@app.route("/api/pacientes", methods=["POST"])
def criar_paciente():
    d = body()
    err = obrigatorios(d, ["nome", "cpf", "data_nascimento", "telefone", "grupo_sanguineo"])
    if err:
        return jsonify({"erro": err}), 400

    def op(s):
        pessoa = inserir_pessoa(s, d)
        s.add(Paciente(
            id_pessoa=pessoa.id_pessoa,
            num_convenio=d.get("num_convenio") or None,
            grupo_sanguineo=d["grupo_sanguineo"],
        ))
        s.flush()
        sincronizar_alergias(s, pessoa.id_pessoa, d.get("alergias") or [])
        return {"id_pessoa": pessoa.id_pessoa}

    res, err = escrever(op)
    return (jsonify({"erro": err}), 400) if err else (jsonify({"msg": "Paciente criado", **res}), 201)


@app.route("/api/pacientes/<int:id_pessoa>", methods=["PUT"])
def atualizar_paciente(id_pessoa):
    # 3.4 — Atualizar os dados de um paciente (endereço ou convênio).
    d = body()

    def op(s):
        paciente = s.get(Paciente, id_pessoa)
        if paciente is None:
            return "nao_encontrado"
        if "endereco" in d:
            paciente.pessoa.endereco = d["endereco"] or None
        if "num_convenio" in d:
            paciente.num_convenio = d["num_convenio"] or None
        if "grupo_sanguineo" in d:
            paciente.grupo_sanguineo = d["grupo_sanguineo"]
        if isinstance(d.get("alergias"), list):
            sincronizar_alergias(s, id_pessoa, d["alergias"])
        return "atualizado"

    res, err = escrever(op)
    if err:
        return jsonify({"erro": err}), 400
    if res == "nao_encontrado":
        return jsonify({"erro": "Paciente não encontrado"}), 404
    return jsonify({"msg": "Paciente atualizado"})


# ============================================================
# Profissionais (residentes e preceptores)
# ============================================================

def atualizar_pessoa_profissional(profissional, d):
    """Atualiza campos comuns de PESSOA e PROFISSIONAL, quando enviados."""
    if "telefone" in d:
        profissional.pessoa.telefone = d["telefone"] or None
    if "endereco" in d:
        profissional.pessoa.endereco = d["endereco"] or None
    if "crm" in d:
        profissional.crm = d["crm"] or None
    if "especialidade" in d:
        profissional.especialidade = d["especialidade"] or None


def json_profissional(sub, extra_campo, extra_valor):
    """Serializa residente/preceptor no mesmo formato que a Etapa 1 devolvia."""
    return {
        "id_pessoa": sub.pessoa.id_pessoa,
        "nome": sub.pessoa.nome,
        "cpf": sub.pessoa.cpf,
        "telefone": sub.pessoa.telefone,
        "crm": sub.profissional.crm,
        "data_admissao": sub.profissional.data_admissao.isoformat(),
        "especialidade": sub.profissional.especialidade,
        extra_campo: extra_valor,
    }


@app.route("/api/residentes")
def listar_residentes():
    # Residente.profissional e Profissional.pessoa são eager "joined": o
    # encadeamento residente -> profissional -> pessoa vem em um único SELECT.
    s = SessionLocal()
    try:
        residentes = (
            s.query(Residente)
             .join(Residente.profissional).join(Profissional.pessoa)
             .order_by(Pessoa.nome)
             .all()
        )
        return jsonify([json_profissional(r, "ano_residencia", r.ano_residencia)
                        for r in residentes])
    finally:
        s.close()


@app.route("/api/residentes", methods=["POST"])
def criar_residente():
    d = body()
    err = obrigatorios(d, ["nome", "cpf", "data_nascimento", "telefone",
                           "crm", "data_admissao", "especialidade", "ano_residencia"])
    if err:
        return jsonify({"erro": err}), 400

    def op(s):
        pessoa = inserir_profissional(s, d)
        s.add(Residente(id_profissional=pessoa.id_pessoa, ano_residencia=d["ano_residencia"]))
        return {"id_pessoa": pessoa.id_pessoa}

    res, err = escrever(op)
    return (jsonify({"erro": err}), 400) if err else (jsonify({"msg": "Residente criado", **res}), 201)


@app.route("/api/residentes/<int:id_pessoa>", methods=["PUT"])
def atualizar_residente(id_pessoa):
    d = body()

    def op(s):
        residente = s.get(Residente, id_pessoa)
        if residente is None:
            return "nao_encontrado"
        atualizar_pessoa_profissional(residente.profissional, d)
        if "ano_residencia" in d:
            residente.ano_residencia = d["ano_residencia"]
        return "atualizado"

    res, err = escrever(op)
    if err:
        return jsonify({"erro": err}), 400
    if res == "nao_encontrado":
        return jsonify({"erro": "Residente não encontrado"}), 404
    return jsonify({"msg": "Residente atualizado"})


@app.route("/api/preceptores")
def listar_preceptores():
    s = SessionLocal()
    try:
        preceptores = (
            s.query(Preceptor)
             .join(Preceptor.profissional).join(Profissional.pessoa)
             .order_by(Pessoa.nome)
             .all()
        )
        return jsonify([json_profissional(p, "titulacao", p.titulacao) for p in preceptores])
    finally:
        s.close()


@app.route("/api/preceptores", methods=["POST"])
def criar_preceptor():
    d = body()
    err = obrigatorios(d, ["nome", "cpf", "data_nascimento", "telefone",
                           "crm", "data_admissao", "especialidade", "titulacao"])
    if err:
        return jsonify({"erro": err}), 400

    def op(s):
        pessoa = inserir_profissional(s, d)
        s.add(Preceptor(id_profissional=pessoa.id_pessoa, titulacao=d["titulacao"]))
        return {"id_pessoa": pessoa.id_pessoa}

    res, err = escrever(op)
    return (jsonify({"erro": err}), 400) if err else (jsonify({"msg": "Preceptor criado", **res}), 201)


@app.route("/api/preceptores/<int:id_pessoa>", methods=["PUT"])
def atualizar_preceptor(id_pessoa):
    d = body()

    def op(s):
        preceptor = s.get(Preceptor, id_pessoa)
        if preceptor is None:
            return "nao_encontrado"
        atualizar_pessoa_profissional(preceptor.profissional, d)
        if "titulacao" in d:
            preceptor.titulacao = d["titulacao"]
        return "atualizado"

    res, err = escrever(op)
    if err:
        return jsonify({"erro": err}), 400
    if res == "nao_encontrado":
        return jsonify({"erro": "Preceptor não encontrado"}), 404
    return jsonify({"msg": "Preceptor atualizado"})


# ============================================================
# Unidades
# ============================================================

@app.route("/api/unidades")
def listar_unidades():
    s = SessionLocal()
    try:
        unidades = s.query(Unidade).order_by(Unidade.nome).all()
        return jsonify([
            {"id_unidade": u.id_unidade, "nome": u.nome,
             "tipo": u.tipo, "capacidade_leitos": u.capacidade_leitos}
            for u in unidades
        ])
    finally:
        s.close()


@app.route("/api/unidades", methods=["POST"])
def criar_unidade():
    d = body()
    err = obrigatorios(d, ["nome", "tipo", "capacidade_leitos"])
    if err:
        return jsonify({"erro": err}), 400

    def op(s):
        unidade = Unidade(
            nome=d["nome"],
            tipo=d["tipo"],
            capacidade_leitos=inteiro(d["capacidade_leitos"], "capacidade_leitos"),
        )
        s.add(unidade)
        s.flush()
        return {"id_unidade": unidade.id_unidade}

    res, err = escrever(op)
    return (jsonify({"erro": err}), 400) if err else (jsonify({"msg": "Unidade criada", **res}), 201)


@app.route("/api/unidades/<int:id_unidade>", methods=["PUT"])
def atualizar_unidade(id_unidade):
    d = body()
    err = obrigatorios(d, ["nome", "tipo", "capacidade_leitos"])
    if err:
        return jsonify({"erro": err}), 400

    def op(s):
        unidade = s.get(Unidade, id_unidade)
        if unidade is None:
            return "nao_encontrado"
        unidade.nome = d["nome"]
        unidade.tipo = d["tipo"]
        unidade.capacidade_leitos = inteiro(d["capacidade_leitos"], "capacidade_leitos")
        return "atualizado"

    res, err = escrever(op)
    if err:
        return jsonify({"erro": err}), 400
    if res == "nao_encontrado":
        return jsonify({"erro": "Unidade não encontrada"}), 404
    return jsonify({"msg": "Unidade atualizada"})


# ============================================================
# Escalas (listagem com filtros + cadastro)
# ============================================================

@app.route("/api/escalas")
def listar_escalas():
    s = SessionLocal()
    try:
        # contains_eager reaproveita o JOIN que já é feito para ordenar por
        # Unidade.nome, em vez de o eager loader abrir um segundo JOIN da unidade.
        # Escala.residente e Escala.preceptor continuam com o eager "joined" padrão
        # declarado no model, trazendo residente/preceptor -> profissional -> pessoa.
        q = (s.query(Escala)
              .join(Escala.unidade)
              .options(contains_eager(Escala.unidade)))

        if request.args.get("unidade"):
            q = q.filter(Escala.id_unidade == inteiro(request.args["unidade"], "unidade"))
        if request.args.get("dia"):
            q = q.filter(Escala.dia_semana == request.args["dia"])
        if request.args.get("turno"):
            q = q.filter(Escala.turno == request.args["turno"])

        escalas = q.order_by(Unidade.nome, Escala.dia_semana, Escala.turno).all()
        return jsonify([
            {
                "id_escala": e.id_escala,
                "id_unidade": e.id_unidade,
                "unidade": e.unidade.nome,
                "dia_semana": e.dia_semana,
                "turno": e.turno,
                "id_residente": e.id_residente,
                "residente": e.residente.pessoa.nome,
                "id_preceptor": e.id_preceptor,
                "preceptor": e.preceptor.pessoa.nome,
            }
            for e in escalas
        ])
    except ValueError as exc:
        return jsonify({"erro": str(exc)}), 400
    finally:
        s.close()


@app.route("/api/escalas", methods=["POST"])
def criar_escala():
    d = body()
    err = obrigatorios(d, ["id_unidade", "dia_semana", "turno", "id_residente", "id_preceptor"])
    if err:
        return jsonify({"erro": err}), 400

    def op(s):
        escala = Escala(
            id_unidade=inteiro(d["id_unidade"], "id_unidade"),
            dia_semana=d["dia_semana"],
            turno=d["turno"],
            id_residente=inteiro(d["id_residente"], "id_residente"),
            id_preceptor=inteiro(d["id_preceptor"], "id_preceptor"),
        )
        s.add(escala)
        s.flush()
        return {"id_escala": escala.id_escala}

    res, err = escrever(op)
    return (jsonify({"erro": err}), 400) if err else (jsonify({"msg": "Escala criada", **res}), 201)


def lookup(model, coluna_id):
    """Lista {id, nome} de um subtipo de pessoa, ordenado por nome."""
    s = SessionLocal()
    try:
        linhas = (s.query(coluna_id, Pessoa.nome)
                   .join(Pessoa, Pessoa.id_pessoa == coluna_id)
                   .order_by(Pessoa.nome)
                   .all())
        return jsonify([{"id": id_, "nome": nome} for id_, nome in linhas])
    finally:
        s.close()


@app.route("/api/residentes-lookup")
def residentes_lookup():
    return lookup(Residente, Residente.id_profissional)


@app.route("/api/preceptores-lookup")
def preceptores_lookup():
    return lookup(Preceptor, Preceptor.id_profissional)


@app.route("/api/pacientes-lookup")
def pacientes_lookup():
    return lookup(Paciente, Paciente.id_pessoa)


@app.route("/api/procedimentos")
def procedimentos_lookup():
    return jsonify(query(
        """
        SELECT id_procedimento AS id, codigo, nome, tempo_medio_minutos, nivel_risco
          FROM procedimento
         ORDER BY nome
        """
    ))


@app.route("/api/atendimentos")
def listar_atendimentos():
    return jsonify(query(
        """
        SELECT a.id_atendimento,
               to_char(a.data_hora, 'DD/MM/YYYY HH24:MI') AS data_hora,
               a.duracao_minutos,
               pac.nome  AS paciente,
               res.nome  AS residente,
               prec.nome AS preceptor
          FROM atendimento a
          JOIN pessoa pac  ON pac.id_pessoa  = a.id_paciente
          JOIN pessoa res  ON res.id_pessoa  = a.id_residente
          JOIN pessoa prec ON prec.id_pessoa = a.id_preceptor
         ORDER BY a.data_hora DESC
        """
    ))


@app.route("/api/atendimentos", methods=["POST"])
def criar_atendimento():
    data = request.get_json(silent=True) or {}
    try:
        params = (
            data["data_hora"],
            int(data["duracao_minutos"]),
            int(data["id_paciente"]),
            int(data["id_residente"]),
            int(data["id_preceptor"]),
        )
    except (KeyError, TypeError, ValueError):
        return jsonify({"erro": "Campos obrigatórios: data_hora, duracao_minutos, id_paciente, id_residente, id_preceptor"}), 400

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                WITH params AS (
                    SELECT %s::timestamp AS data_hora,
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
                       (SELECT id_atendimento FROM inserido) AS id_atendimento
                """,
                params,
            )
            row = cur.fetchone()
        conn.commit()
        if row["status"] != "inserido":
            return jsonify({"erro": row["status"].replace("_", " ").capitalize()}), 400
        return jsonify({"id_atendimento": row["id_atendimento"]})
    except psycopg2.Error as exc:
        conn.rollback()
        msg = (exc.diag.message_primary if exc.diag else None) or str(exc)
        return jsonify({"erro": msg}), 400
    finally:
        conn.close()


@app.route("/api/atendimentos/<int:id_atendimento>/procedimentos")
def procedimentos_do_atendimento(id_atendimento):
    return jsonify(query(
        """
        SELECT proc.id_procedimento,
               proc.codigo,
               proc.nome AS procedimento,
               proc.nivel_risco,
               pr.quantidade,
               pr.tempo_real_minutos,
               pr.observacao,
               pr.faturado
          FROM procedimento_realizado pr
          JOIN procedimento proc ON proc.id_procedimento = pr.id_procedimento
         WHERE pr.id_atendimento = %s
         ORDER BY proc.nome
        """,
        (id_atendimento,),
    ))


@app.route("/api/atendimentos/<int:id_atendimento>/procedimentos", methods=["POST"])
def adicionar_procedimento_realizado(id_atendimento):
    data = request.get_json(silent=True) or {}
    try:
        params = (
            id_atendimento,
            int(data["id_procedimento"]),
            int(data["quantidade"]),
            int(data["tempo_real_minutos"]),
            (data.get("observacao") or None),
        )
    except (KeyError, TypeError, ValueError):
        return jsonify({"erro": "Campos obrigatórios: id_procedimento, quantidade, tempo_real_minutos"}), 400

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO procedimento_realizado
                    (id_atendimento, id_procedimento, quantidade, tempo_real_minutos, observacao)
                VALUES (%s, %s, %s, %s, %s)
                """,
                params,
            )
        conn.commit()
        return jsonify({"msg": "Procedimento adicionado"})
    except psycopg2.Error as exc:
        conn.rollback()
        msg = (exc.diag.message_primary if exc.diag else None) or str(exc)
        return jsonify({"erro": msg}), 400
    finally:
        conn.close()


@app.route("/api/atendimentos/<int:id_atendimento>/procedimentos/<int:id_procedimento>", methods=["DELETE"])
def remover_procedimento_realizado(id_atendimento, id_procedimento):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
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
                       END AS status
                """,
                (id_atendimento, id_procedimento),
            )
            status = cur.fetchone()["status"]
        conn.commit()
        if status == "removido":
            return jsonify({"msg": "Procedimento removido"})
        if status == "bloqueado_faturado":
            return jsonify({"erro": "Não é possível remover: procedimento já foi faturado"}), 409
        return jsonify({"erro": "Procedimento não encontrado"}), 404
    finally:
        conn.close()


@app.route("/api/analiticas/ranking-residentes")
def ranking_residentes():
    return jsonify(query(
        """
        SELECT p.nome                  AS residente,
               COUNT(a.id_atendimento) AS total_atendimentos
          FROM residente r
          JOIN pessoa p           ON p.id_pessoa    = r.id_profissional
          LEFT JOIN atendimento a ON a.id_residente = r.id_profissional
         GROUP BY p.id_pessoa, p.nome
         ORDER BY total_atendimentos DESC
        """
    ))


@app.route("/api/analiticas/preceptores-ativos")
def preceptores_ativos():
    try:
        ano = int(request.args.get("ano"))
        mes = int(request.args.get("mes"))
    except (TypeError, ValueError):
        return jsonify({"erro": "Parâmetros ano e mes são obrigatórios"}), 400

    return jsonify(query(
        """
        SELECT p.nome                  AS preceptor,
               COUNT(a.id_atendimento) AS total_atendimentos
          FROM preceptor prec
          JOIN pessoa p      ON p.id_pessoa    = prec.id_profissional
          JOIN atendimento a ON a.id_preceptor = prec.id_profissional
         WHERE EXTRACT(YEAR  FROM a.data_hora) = %s
           AND EXTRACT(MONTH FROM a.data_hora) = %s
         GROUP BY p.id_pessoa, p.nome
        HAVING COUNT(a.id_atendimento) > 5
         ORDER BY total_atendimentos DESC
        """,
        (ano, mes),
    ))


DIAS_SEMANA = ["Segunda", "Terca", "Quarta", "Quinta", "Sexta", "Sabado", "Domingo"]


def ocorrencias_por_dia_no_mes_corrente():
    """
    Quantas vezes cada dia da semana ocorre no mês corrente.
    Ex.: {'Segunda': 4, 'Terca': 5, ...}
    """
    hoje = date.today()
    _, ultimo_dia = calendar.monthrange(hoje.year, hoje.month)
    contagem = {dia: 0 for dia in DIAS_SEMANA}
    for numero in range(1, ultimo_dia + 1):
        contagem[DIAS_SEMANA[date(hoje.year, hoje.month, numero).weekday()]] += 1
    return contagem


@app.route("/api/analiticas/plantoes-por-residente")
def plantoes_por_residente():
    # 4.3 — Plantões escalados por residente, em cada unidade, no mês corrente.
    #
    # A versão SQL da Etapa 1 gerava os dias do mês com generate_series e fazia JOIN
    # para multiplicar cada escala pelo número de vezes que aquele dia da semana cai
    # no mês. Na ORM, esse calendário é calculado em Python (calendar/date) e entra
    # na query como um CASE — assim a agregação continua no banco, sem SQL cru.
    peso_do_dia = ocorrencias_por_dia_no_mes_corrente()

    s = SessionLocal()
    try:
        qtd_plantoes = func.sum(case(peso_do_dia, value=Escala.dia_semana, else_=0))
        linhas = (
            s.query(Unidade.nome, Pessoa.nome, qtd_plantoes)
             .select_from(Escala)
             .join(Unidade, Unidade.id_unidade == Escala.id_unidade)
             .join(Residente, Residente.id_profissional == Escala.id_residente)
             .join(Pessoa, Pessoa.id_pessoa == Residente.id_profissional)
             .group_by(Unidade.nome, Pessoa.nome)
             .order_by(Unidade.nome, qtd_plantoes.desc())
             .all()
        )
        return jsonify([
            {"unidade": unidade, "residente": residente, "qtd_plantoes": int(qtd)}
            for unidade, residente, qtd in linhas
        ])
    finally:
        s.close()


@app.route("/api/analiticas/pacientes-sem-risco-alto")
def pacientes_sem_risco_alto():
    # 4.4 — Pacientes que nunca realizaram procedimento de nível de risco 'ALTO'.
    return jsonify(query(
        """
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
                     JOIN procedimento_realizado pr ON pr.id_atendimento    = a.id_atendimento
                     JOIN procedimento proc         ON proc.id_procedimento = pr.id_procedimento
                    WHERE a.id_paciente = pac.id_pessoa
                      AND proc.nivel_risco = 'ALTO'
               )
         ORDER BY p.nome
        """
    ))


@app.route("/api/pacientes/<int:id_pessoa>/atendimentos")
def atendimentos_do_paciente(id_pessoa):
    # 3.2 — Atendimentos de um paciente específico ordenados por data (mais recente primeiro).
    return jsonify(query(
        """
        SELECT a.id_atendimento,
               to_char(a.data_hora, 'DD/MM/YYYY HH24:MI') AS data_hora,
               a.duracao_minutos,
               res.nome AS residente,
               pre.nome AS preceptor
          FROM atendimento a
          JOIN pessoa res ON res.id_pessoa = a.id_residente
          JOIN pessoa pre ON pre.id_pessoa = a.id_preceptor
         WHERE a.id_paciente = %s
         ORDER BY a.data_hora DESC
        """,
        (id_pessoa,),
    ))


if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv("PORT", "8000")))
