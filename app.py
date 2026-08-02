"""
Servidor do Hospital Dra. Yuska Maritan Brito.

Etapa 1: Flask + psycopg2 (SQL puro).
Etapa 2: tudo migrado para SQLAlchemy — ver orm/models.py e orm/db.py. Não sobrou
nenhum endpoint em SQL puro; a conexão com o banco é só a engine do ORM.

Rodar:  python app.py   ->   http://localhost:8000
Config do banco via variáveis de ambiente (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD).
"""
import os
import calendar
from datetime import date, datetime

from flask import Flask, jsonify, request
from sqlalchemy import case, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import contains_eager

from orm.db import SessionLocal
from orm.models import (
    Alergia, Atendimento, Escala, Paciente, PacienteAlergia, Pessoa, Preceptor,
    Procedimento, ProcedimentoRealizado, Profissional, Residente, Unidade,
)

app = Flask(__name__, static_folder="frontend", static_url_path="")


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


def data_hora_iso(valor, campo):
    """Converte o valor de um <input type="datetime-local"> em datetime."""
    try:
        return datetime.fromisoformat(valor)
    except (TypeError, ValueError):
        raise ValueError(f"Campo {campo} deve estar no formato AAAA-MM-DDTHH:MM.")


def formatar_data_hora(valor):
    """Mesmo formato que o to_char(..., 'DD/MM/YYYY HH24:MI') da Etapa 1."""
    return valor.strftime("%d/%m/%Y %H:%M")


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
        "pk_procedimento_realizado": "Esse procedimento já foi registrado neste atendimento.",
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
    s = SessionLocal()
    try:
        def total(model):
            return s.query(func.count()).select_from(model).scalar()

        return jsonify({
            "pacientes": total(Paciente),
            "residentes": total(Residente),
            "preceptores": total(Preceptor),
            "atendimentos": total(Atendimento),
        })
    finally:
        s.close()


@app.route("/api/atendimentos-recentes")
def atendimentos_recentes():
    s = SessionLocal()
    try:
        atendimentos = (s.query(Atendimento)
                         .order_by(Atendimento.data_hora.desc())
                         .limit(10)
                         .all())
        return jsonify([
            {
                "data_hora": formatar_data_hora(a.data_hora),
                "paciente": a.paciente.pessoa.nome,
                "residente": a.residente.pessoa.nome,
                "preceptor": a.preceptor.pessoa.nome,
                "duracao_minutos": a.duracao_minutos,
            }
            for a in atendimentos
        ])
    finally:
        s.close()


@app.route("/api/tempo-medio-residente")
def tempo_medio_residente():
    # 3.6 — Tempo médio de duração dos atendimentos por residente.
    s = SessionLocal()
    try:
        qtd = func.count(Atendimento.id_atendimento)
        media = func.round(func.avg(Atendimento.duracao_minutos), 1)
        linhas = (
            s.query(Pessoa.nome, qtd, media)
             .select_from(Residente)
             .join(Pessoa, Pessoa.id_pessoa == Residente.id_profissional)
             .join(Atendimento, Atendimento.id_residente == Residente.id_profissional)
             .group_by(Pessoa.id_pessoa, Pessoa.nome)
             .order_by(media.desc())
             .all()
        )
        return jsonify([
            {"residente": nome, "qtd_atendimentos": qtd_, "tempo_medio_minutos": float(media_)}
            for nome, qtd_, media_ in linhas
        ])
    finally:
        s.close()


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
    s = SessionLocal()
    try:
        procedimentos = s.query(Procedimento).order_by(Procedimento.nome).all()
        return jsonify([
            {
                "id": p.id_procedimento,
                "codigo": p.codigo,
                "nome": p.nome,
                "tempo_medio_minutos": p.tempo_medio_minutos,
                "nivel_risco": p.nivel_risco,
            }
            for p in procedimentos
        ])
    finally:
        s.close()


@app.route("/api/atendimentos")
def listar_atendimentos():
    s = SessionLocal()
    try:
        atendimentos = s.query(Atendimento).order_by(Atendimento.data_hora.desc()).all()
        return jsonify([
            {
                "id_atendimento": a.id_atendimento,
                "data_hora": formatar_data_hora(a.data_hora),
                "duracao_minutos": a.duracao_minutos,
                "paciente": a.paciente.pessoa.nome,
                "residente": a.residente.pessoa.nome,
                "preceptor": a.preceptor.pessoa.nome,
            }
            for a in atendimentos
        ])
    finally:
        s.close()


@app.route("/api/atendimentos", methods=["POST"])
def criar_atendimento():
    # 3.1 — Inserir atendimento verificando a existência das FKs.
    d = body()
    err = obrigatorios(d, ["data_hora", "duracao_minutos", "id_paciente",
                           "id_residente", "id_preceptor"])
    if err:
        return jsonify({"erro": err}), 400

    def op(s):
        # Checagem explícita para dizer QUAL FK está errada; sem isso o banco
        # devolveria só "viola a chave estrangeira", sem apontar o campo.
        alvos = [
            (Paciente, "id_paciente", "Paciente inexistente"),
            (Residente, "id_residente", "Residente inexistente"),
            (Preceptor, "id_preceptor", "Preceptor inexistente"),
        ]
        ids = {}
        for model, campo, mensagem in alvos:
            ids[campo] = inteiro(d[campo], campo)
            if s.get(model, ids[campo]) is None:
                raise ValueError(mensagem)

        atendimento = Atendimento(
            data_hora=data_hora_iso(d["data_hora"], "data_hora"),
            duracao_minutos=inteiro(d["duracao_minutos"], "duracao_minutos"),
            id_unidade=inteiro(d["id_unidade"], "id_unidade") if d.get("id_unidade") else None,
            **ids,
        )
        s.add(atendimento)
        s.flush()
        return {"id_atendimento": atendimento.id_atendimento}

    res, err = escrever(op)
    return (jsonify({"erro": err}), 400) if err else jsonify(res)


@app.route("/api/atendimentos/<int:id_atendimento>/procedimentos")
def procedimentos_do_atendimento(id_atendimento):
    # 3.3 — Procedimentos realizados em um atendimento.
    s = SessionLocal()
    try:
        # ProcedimentoRealizado.procedimento é eager "joined", então o JOIN já
        # acontece; o join explícito aqui é só para poder ordenar pelo nome.
        realizados = (
            s.query(ProcedimentoRealizado)
             .join(ProcedimentoRealizado.procedimento)
             .filter(ProcedimentoRealizado.id_atendimento == id_atendimento)
             .order_by(Procedimento.nome)
             .all()
        )
        return jsonify([
            {
                "id_procedimento": pr.id_procedimento,
                "codigo": pr.procedimento.codigo,
                "procedimento": pr.procedimento.nome,
                "nivel_risco": pr.procedimento.nivel_risco,
                "quantidade": pr.quantidade,
                "tempo_real_minutos": pr.tempo_real_minutos,
                "observacao": pr.observacao,
                "faturado": pr.faturado,
            }
            for pr in realizados
        ])
    finally:
        s.close()


@app.route("/api/atendimentos/<int:id_atendimento>/procedimentos", methods=["POST"])
def adicionar_procedimento_realizado(id_atendimento):
    d = body()
    err = obrigatorios(d, ["id_procedimento", "quantidade", "tempo_real_minutos"])
    if err:
        return jsonify({"erro": err}), 400

    def op(s):
        if s.get(Atendimento, id_atendimento) is None:
            raise ValueError("Atendimento inexistente")
        id_procedimento = inteiro(d["id_procedimento"], "id_procedimento")
        if s.get(Procedimento, id_procedimento) is None:
            raise ValueError("Procedimento inexistente")

        # hora_inicio alimenta a sp_calcular_tempo_medio_espera. O formulário não
        # tem esse campo, então o padrão é agora — quando o registro foi feito.
        hora_inicio = (data_hora_iso(d["hora_inicio"], "hora_inicio")
                       if d.get("hora_inicio") else datetime.now())

        s.add(ProcedimentoRealizado(
            id_atendimento=id_atendimento,
            id_procedimento=id_procedimento,
            quantidade=inteiro(d["quantidade"], "quantidade"),
            tempo_real_minutos=inteiro(d["tempo_real_minutos"], "tempo_real_minutos"),
            observacao=d.get("observacao") or None,
            hora_inicio=hora_inicio,
        ))
        s.flush()
        return {"msg": "Procedimento adicionado"}

    res, err = escrever(op)
    return (jsonify({"erro": err}), 400) if err else jsonify(res)


@app.route("/api/atendimentos/<int:id_atendimento>/procedimentos/<int:id_procedimento>", methods=["DELETE"])
def remover_procedimento_realizado(id_atendimento, id_procedimento):
    # 3.5 — Remover procedimento realizado apenas se ainda não foi faturado.
    def op(s):
        realizado = s.get(ProcedimentoRealizado, (id_atendimento, id_procedimento))
        if realizado is None:
            return "nao_encontrado"
        if realizado.faturado:
            return "bloqueado_faturado"
        s.delete(realizado)
        return "removido"

    res, err = escrever(op)
    if err:
        return jsonify({"erro": err}), 400
    if res == "bloqueado_faturado":
        return jsonify({"erro": "Não é possível remover: procedimento já foi faturado"}), 409
    if res == "nao_encontrado":
        return jsonify({"erro": "Procedimento não encontrado"}), 404
    return jsonify({"msg": "Procedimento removido"})


@app.route("/api/analiticas/ranking-residentes")
def ranking_residentes():
    # 4.1 — Ranking dos residentes por número de atendimentos.
    s = SessionLocal()
    try:
        # LEFT JOIN de propósito: residente sem nenhum atendimento entra com zero.
        total = func.count(Atendimento.id_atendimento)
        linhas = (
            s.query(Pessoa.nome, total)
             .select_from(Residente)
             .join(Pessoa, Pessoa.id_pessoa == Residente.id_profissional)
             .outerjoin(Atendimento, Atendimento.id_residente == Residente.id_profissional)
             .group_by(Pessoa.id_pessoa, Pessoa.nome)
             .order_by(total.desc())
             .all()
        )
        return jsonify([
            {"residente": nome, "total_atendimentos": qtd} for nome, qtd in linhas
        ])
    finally:
        s.close()


@app.route("/api/analiticas/preceptores-ativos")
def preceptores_ativos():
    # 4.2 — Preceptores com mais de 5 atendimentos em um mês.
    try:
        ano = int(request.args.get("ano"))
        mes = int(request.args.get("mes"))
    except (TypeError, ValueError):
        return jsonify({"erro": "Parâmetros ano e mes são obrigatórios"}), 400

    s = SessionLocal()
    try:
        total = func.count(Atendimento.id_atendimento)
        linhas = (
            s.query(Pessoa.nome, total)
             .select_from(Preceptor)
             .join(Pessoa, Pessoa.id_pessoa == Preceptor.id_profissional)
             .join(Atendimento, Atendimento.id_preceptor == Preceptor.id_profissional)
             .filter(func.extract("year", Atendimento.data_hora) == ano,
                     func.extract("month", Atendimento.data_hora) == mes)
             .group_by(Pessoa.id_pessoa, Pessoa.nome)
             .having(total > 5)
             .order_by(total.desc())
             .all()
        )
        return jsonify([
            {"preceptor": nome, "total_atendimentos": qtd} for nome, qtd in linhas
        ])
    finally:
        s.close()


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
    s = SessionLocal()
    try:
        # Correlacionado com o paciente de fora, igual ao NOT EXISTS da Etapa 1.
        tem_risco_alto = (
            s.query(Atendimento.id_atendimento)
             .join(ProcedimentoRealizado,
                   ProcedimentoRealizado.id_atendimento == Atendimento.id_atendimento)
             .join(Procedimento,
                   Procedimento.id_procedimento == ProcedimentoRealizado.id_procedimento)
             .filter(Atendimento.id_paciente == Paciente.id_pessoa,
                     Procedimento.nivel_risco == "ALTO")
             .exists()
        )
        linhas = (
            s.query(Pessoa.id_pessoa, Pessoa.nome, Pessoa.cpf,
                    Paciente.num_convenio, Paciente.grupo_sanguineo)
             .select_from(Paciente)
             .join(Pessoa, Pessoa.id_pessoa == Paciente.id_pessoa)
             .filter(~tem_risco_alto)
             .order_by(Pessoa.nome)
             .all()
        )
        return jsonify([
            {"id_pessoa": id_, "nome": nome, "cpf": cpf,
             "num_convenio": convenio, "grupo_sanguineo": grupo}
            for id_, nome, cpf, convenio, grupo in linhas
        ])
    finally:
        s.close()


@app.route("/api/pacientes/<int:id_pessoa>/atendimentos")
def atendimentos_do_paciente(id_pessoa):
    # 3.2 — Atendimentos de um paciente específico, do mais recente para o mais antigo.
    s = SessionLocal()
    try:
        atendimentos = (
            s.query(Atendimento)
             .filter(Atendimento.id_paciente == id_pessoa)
             .order_by(Atendimento.data_hora.desc())
             .all()
        )
        return jsonify([
            {
                "id_atendimento": a.id_atendimento,
                "data_hora": formatar_data_hora(a.data_hora),
                "duracao_minutos": a.duracao_minutos,
                "residente": a.residente.pessoa.nome,
                "preceptor": a.preceptor.pessoa.nome,
            }
            for a in atendimentos
        ])
    finally:
        s.close()


if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv("PORT", "8000")))
