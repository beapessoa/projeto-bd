"""
Servidor do Hospital Dra. Yuska Maritan Brito.
Flask + psycopg2 (SQL puro, sem ORM): serve o frontend e roda as queries.

Rodar:  python app.py   ->   http://localhost:8000
Config do banco via variáveis de ambiente (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD).
"""
import os
import getpass
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, jsonify, request

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


def write(fn):
    """Roda fn(cur) numa transação. Devolve (resultado, None) ou (None, mensagem_erro)."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            result = fn(cur)
        conn.commit()
        return result, None
    except psycopg2.Error as exc:
        conn.rollback()
        msg = (exc.diag.message_primary if exc.diag else None) or str(exc)
        return None, amigavel(msg)
    finally:
        conn.close()


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


def inserir_pessoa(cur, d):
    """Insere na tabela PESSOA (supertipo) e devolve o id gerado."""
    cur.execute(
        "INSERT INTO pessoa (nome, cpf, data_nascimento, telefone, endereco, is_flamengo) "
        "VALUES (%s, %s, %s::date, %s, %s, %s) RETURNING id_pessoa",
        (d["nome"], d["cpf"], d["data_nascimento"], d["telefone"],
         d.get("endereco") or None, bool(d.get("is_flamengo", False))),
    )
    return cur.fetchone()["id_pessoa"]


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
    return jsonify(query(
        """
        SELECT p.id_pessoa, p.nome, p.cpf, p.endereco,
               pac.num_convenio, pac.grupo_sanguineo,
               COALESCE(ARRAY_AGG(al.nome ORDER BY al.nome)
                        FILTER (WHERE al.nome IS NOT NULL), '{}') AS alergias
          FROM paciente pac
          JOIN pessoa p ON p.id_pessoa = pac.id_pessoa
          LEFT JOIN paciente_alergia pa ON pa.id_paciente = pac.id_pessoa
          LEFT JOIN alergia al          ON al.id_alergia  = pa.id_alergia
         GROUP BY p.id_pessoa, p.nome, p.cpf, p.endereco, pac.num_convenio, pac.grupo_sanguineo
         ORDER BY p.nome
        """
    ))


def sincronizar_alergias(cur, id_paciente, alergias):
    """Reescreve o conjunto de alergias (N:N) do paciente."""
    cur.execute("DELETE FROM paciente_alergia WHERE id_paciente = %s", (id_paciente,))
    for nome in alergias:
        nome = (nome or "").strip()
        if not nome:
            continue
        cur.execute("INSERT INTO alergia (nome) VALUES (%s) ON CONFLICT (nome) DO NOTHING", (nome,))
        cur.execute("SELECT id_alergia FROM alergia WHERE nome = %s", (nome,))
        cur.execute(
            "INSERT INTO paciente_alergia (id_paciente, id_alergia) VALUES (%s, %s) "
            "ON CONFLICT DO NOTHING",
            (id_paciente, cur.fetchone()["id_alergia"]),
        )


@app.route("/api/pacientes", methods=["POST"])
def criar_paciente():
    d = body()
    err = obrigatorios(d, ["nome", "cpf", "data_nascimento", "telefone", "grupo_sanguineo"])
    if err:
        return jsonify({"erro": err}), 400

    def op(cur):
        pid = inserir_pessoa(cur, d)
        cur.execute(
            "INSERT INTO paciente (id_pessoa, num_convenio, grupo_sanguineo) VALUES (%s, %s, %s)",
            (pid, d.get("num_convenio") or None, d["grupo_sanguineo"]),
        )
        sincronizar_alergias(cur, pid, d.get("alergias") or [])
        return {"id_pessoa": pid}

    res, err = write(op)
    return (jsonify({"erro": err}), 400) if err else (jsonify({"msg": "Paciente criado", **res}), 201)


@app.route("/api/pacientes/<int:id_pessoa>", methods=["PUT"])
def atualizar_paciente(id_pessoa):
    d = body()
    if not query("SELECT 1 FROM paciente WHERE id_pessoa = %s", (id_pessoa,)):
        return jsonify({"erro": "Paciente não encontrado"}), 404

    def op(cur):
        if "endereco" in d:
            cur.execute("UPDATE pessoa SET endereco = %s WHERE id_pessoa = %s",
                        (d["endereco"] or None, id_pessoa))
        sets, vals = [], []
        if "num_convenio" in d:
            sets.append("num_convenio = %s")
            vals.append(d["num_convenio"] or None)
        if "grupo_sanguineo" in d:
            sets.append("grupo_sanguineo = %s")
            vals.append(d["grupo_sanguineo"])
        if sets:
            vals.append(id_pessoa)
            cur.execute(f"UPDATE paciente SET {', '.join(sets)} WHERE id_pessoa = %s", vals)
        if isinstance(d.get("alergias"), list):
            sincronizar_alergias(cur, id_pessoa, d["alergias"])

    _, err = write(op)
    return (jsonify({"erro": err}), 400) if err else jsonify({"msg": "Paciente atualizado"})


# ============================================================
# Profissionais (residentes e preceptores)
# ============================================================

def atualizar_pessoa_profissional(cur, id_pessoa, d):
    """Atualiza campos comuns de PESSOA e PROFISSIONAL, quando enviados."""
    for tabela, campos in (
        ("pessoa", ["telefone", "endereco"]),
        ("profissional", ["crm", "especialidade"]),
    ):
        sets = [f"{c} = %s" for c in campos if c in d]
        vals = [d[c] or None for c in campos if c in d]
        if sets:
            vals.append(id_pessoa)
            cur.execute(f"UPDATE {tabela} SET {', '.join(sets)} WHERE id_pessoa = %s", vals)


@app.route("/api/residentes")
def listar_residentes():
    return jsonify(query(
        """
        SELECT p.id_pessoa, p.nome, p.cpf, p.telefone, prof.crm,
               to_char(prof.data_admissao, 'YYYY-MM-DD') AS data_admissao,
               prof.especialidade, r.ano_residencia
          FROM residente r
          JOIN profissional prof ON prof.id_pessoa = r.id_profissional
          JOIN pessoa p          ON p.id_pessoa    = prof.id_pessoa
         ORDER BY p.nome
        """
    ))


@app.route("/api/residentes", methods=["POST"])
def criar_residente():
    d = body()
    err = obrigatorios(d, ["nome", "cpf", "data_nascimento", "telefone",
                           "crm", "data_admissao", "especialidade", "ano_residencia"])
    if err:
        return jsonify({"erro": err}), 400

    def op(cur):
        pid = inserir_pessoa(cur, d)
        cur.execute(
            "INSERT INTO profissional (id_pessoa, crm, data_admissao, especialidade) "
            "VALUES (%s, %s, %s::date, %s)",
            (pid, d["crm"], d["data_admissao"], d["especialidade"]),
        )
        cur.execute("INSERT INTO residente (id_profissional, ano_residencia) VALUES (%s, %s)",
                    (pid, d["ano_residencia"]))
        return {"id_pessoa": pid}

    res, err = write(op)
    return (jsonify({"erro": err}), 400) if err else (jsonify({"msg": "Residente criado", **res}), 201)


@app.route("/api/residentes/<int:id_pessoa>", methods=["PUT"])
def atualizar_residente(id_pessoa):
    d = body()
    if not query("SELECT 1 FROM residente WHERE id_profissional = %s", (id_pessoa,)):
        return jsonify({"erro": "Residente não encontrado"}), 404

    def op(cur):
        atualizar_pessoa_profissional(cur, id_pessoa, d)
        if "ano_residencia" in d:
            cur.execute("UPDATE residente SET ano_residencia = %s WHERE id_profissional = %s",
                        (d["ano_residencia"], id_pessoa))

    _, err = write(op)
    return (jsonify({"erro": err}), 400) if err else jsonify({"msg": "Residente atualizado"})


@app.route("/api/preceptores")
def listar_preceptores():
    return jsonify(query(
        """
        SELECT p.id_pessoa, p.nome, p.cpf, p.telefone, prof.crm,
               to_char(prof.data_admissao, 'YYYY-MM-DD') AS data_admissao,
               prof.especialidade, prec.titulacao
          FROM preceptor prec
          JOIN profissional prof ON prof.id_pessoa = prec.id_profissional
          JOIN pessoa p          ON p.id_pessoa    = prof.id_pessoa
         ORDER BY p.nome
        """
    ))


@app.route("/api/preceptores", methods=["POST"])
def criar_preceptor():
    d = body()
    err = obrigatorios(d, ["nome", "cpf", "data_nascimento", "telefone",
                           "crm", "data_admissao", "especialidade", "titulacao"])
    if err:
        return jsonify({"erro": err}), 400

    def op(cur):
        pid = inserir_pessoa(cur, d)
        cur.execute(
            "INSERT INTO profissional (id_pessoa, crm, data_admissao, especialidade) "
            "VALUES (%s, %s, %s::date, %s)",
            (pid, d["crm"], d["data_admissao"], d["especialidade"]),
        )
        cur.execute("INSERT INTO preceptor (id_profissional, titulacao) VALUES (%s, %s)",
                    (pid, d["titulacao"]))
        return {"id_pessoa": pid}

    res, err = write(op)
    return (jsonify({"erro": err}), 400) if err else (jsonify({"msg": "Preceptor criado", **res}), 201)


@app.route("/api/preceptores/<int:id_pessoa>", methods=["PUT"])
def atualizar_preceptor(id_pessoa):
    d = body()
    if not query("SELECT 1 FROM preceptor WHERE id_profissional = %s", (id_pessoa,)):
        return jsonify({"erro": "Preceptor não encontrado"}), 404

    def op(cur):
        atualizar_pessoa_profissional(cur, id_pessoa, d)
        if "titulacao" in d:
            cur.execute("UPDATE preceptor SET titulacao = %s WHERE id_profissional = %s",
                        (d["titulacao"], id_pessoa))

    _, err = write(op)
    return (jsonify({"erro": err}), 400) if err else jsonify({"msg": "Preceptor atualizado"})


# ============================================================
# Unidades
# ============================================================

@app.route("/api/unidades")
def listar_unidades():
    return jsonify(query(
        "SELECT id_unidade, nome, tipo, capacidade_leitos FROM unidade ORDER BY nome"
    ))


@app.route("/api/unidades", methods=["POST"])
def criar_unidade():
    d = body()
    err = obrigatorios(d, ["nome", "tipo", "capacidade_leitos"])
    if err:
        return jsonify({"erro": err}), 400

    def op(cur):
        cur.execute(
            "INSERT INTO unidade (nome, tipo, capacidade_leitos) VALUES (%s, %s, %s::int) "
            "RETURNING id_unidade",
            (d["nome"], d["tipo"], d["capacidade_leitos"]),
        )
        return {"id_unidade": cur.fetchone()["id_unidade"]}

    res, err = write(op)
    return (jsonify({"erro": err}), 400) if err else (jsonify({"msg": "Unidade criada", **res}), 201)


@app.route("/api/unidades/<int:id_unidade>", methods=["PUT"])
def atualizar_unidade(id_unidade):
    d = body()
    err = obrigatorios(d, ["nome", "tipo", "capacidade_leitos"])
    if err:
        return jsonify({"erro": err}), 400
    if not query("SELECT 1 FROM unidade WHERE id_unidade = %s", (id_unidade,)):
        return jsonify({"erro": "Unidade não encontrada"}), 404

    def op(cur):
        cur.execute(
            "UPDATE unidade SET nome = %s, tipo = %s, capacidade_leitos = %s::int "
            "WHERE id_unidade = %s",
            (d["nome"], d["tipo"], d["capacidade_leitos"], id_unidade),
        )

    _, err = write(op)
    return (jsonify({"erro": err}), 400) if err else jsonify({"msg": "Unidade atualizada"})


# ============================================================
# Escalas (listagem com filtros + cadastro)
# ============================================================

@app.route("/api/escalas")
def listar_escalas():
    where, params = [], []
    if request.args.get("unidade"):
        where.append("e.id_unidade = %s::int")
        params.append(request.args["unidade"])
    if request.args.get("dia"):
        where.append("e.dia_semana = %s")
        params.append(request.args["dia"])
    if request.args.get("turno"):
        where.append("e.turno = %s")
        params.append(request.args["turno"])

    sql = """
        SELECT e.id_escala, e.id_unidade, u.nome AS unidade,
               e.dia_semana, e.turno,
               e.id_residente, res.nome AS residente,
               e.id_preceptor, pre.nome AS preceptor
          FROM escala e
          JOIN unidade u  ON u.id_unidade  = e.id_unidade
          JOIN pessoa res ON res.id_pessoa = e.id_residente
          JOIN pessoa pre ON pre.id_pessoa = e.id_preceptor
    """
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY u.nome, e.dia_semana, e.turno"
    return jsonify(query(sql, params or None))


@app.route("/api/escalas", methods=["POST"])
def criar_escala():
    d = body()
    err = obrigatorios(d, ["id_unidade", "dia_semana", "turno", "id_residente", "id_preceptor"])
    if err:
        return jsonify({"erro": err}), 400

    def op(cur):
        cur.execute(
            "INSERT INTO escala (id_unidade, dia_semana, turno, id_residente, id_preceptor) "
            "VALUES (%s::int, %s, %s, %s::int, %s::int) RETURNING id_escala",
            (d["id_unidade"], d["dia_semana"], d["turno"], d["id_residente"], d["id_preceptor"]),
        )
        return {"id_escala": cur.fetchone()["id_escala"]}

    res, err = write(op)
    return (jsonify({"erro": err}), 400) if err else (jsonify({"msg": "Escala criada", **res}), 201)


if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv("PORT", "8000")))
