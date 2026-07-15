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



@app.route("/")
def index():
    return app.send_static_file("index.html")



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
               pac.nome  AS paciente,
               res.nome  AS residente,
               prec.nome AS preceptor,
               a.duracao_minutos
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


@app.route("/api/pacientes")
def pacientes():
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


@app.route("/api/pacientes/<int:id_pessoa>", methods=["PUT"])
def atualizar_paciente(id_pessoa):
    data = request.get_json(silent=True) or {}
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM paciente WHERE id_pessoa = %s", (id_pessoa,))
            if cur.fetchone() is None:
                return jsonify({"erro": "Paciente não encontrado"}), 404

            if "endereco" in data:
                cur.execute(
                    "UPDATE pessoa SET endereco = %s WHERE id_pessoa = %s",
                    (data["endereco"], id_pessoa),
                )

            sets, vals = [], []
            if "num_convenio" in data:
                sets.append("num_convenio = %s")
                vals.append(data["num_convenio"])
            if "grupo_sanguineo" in data:
                sets.append("grupo_sanguineo = %s")
                vals.append(data["grupo_sanguineo"])
            if sets:
                vals.append(id_pessoa)
                cur.execute(
                    f"UPDATE paciente SET {', '.join(sets)} WHERE id_pessoa = %s", vals
                )

            if isinstance(data.get("alergias"), list):
                cur.execute("DELETE FROM paciente_alergia WHERE id_paciente = %s", (id_pessoa,))
                for nome in data["alergias"]:
                    nome = (nome or "").strip()
                    if not nome:
                        continue
                    cur.execute(
                        "INSERT INTO alergia (nome) VALUES (%s) ON CONFLICT (nome) DO NOTHING",
                        (nome,),
                    )
                    cur.execute("SELECT id_alergia FROM alergia WHERE nome = %s", (nome,))
                    id_alergia = cur.fetchone()["id_alergia"]
                    cur.execute(
                        "INSERT INTO paciente_alergia (id_paciente, id_alergia) "
                        "VALUES (%s, %s) ON CONFLICT DO NOTHING",
                        (id_pessoa, id_alergia),
                    )
        conn.commit()
        return jsonify({"msg": "Paciente atualizado"})
    except psycopg2.Error as exc:
        conn.rollback()
        msg = (exc.diag.message_primary if exc.diag else None) or str(exc)
        return jsonify({"erro": msg}), 400
    finally:
        conn.close()


@app.route("/api/residentes")
def residentes_lookup():
    return jsonify(query(
        """
        SELECT r.id_profissional AS id, p.nome
          FROM residente r
          JOIN pessoa p ON p.id_pessoa = r.id_profissional
         ORDER BY p.nome
        """
    ))


@app.route("/api/preceptores")
def preceptores_lookup():
    return jsonify(query(
        """
        SELECT prec.id_profissional AS id, p.nome
          FROM preceptor prec
          JOIN pessoa p ON p.id_pessoa = prec.id_profissional
         ORDER BY p.nome
        """
    ))


@app.route("/api/pacientes-lookup")
def pacientes_lookup():
    return jsonify(query(
        """
        SELECT pac.id_pessoa AS id, p.nome
          FROM paciente pac
          JOIN pessoa p ON p.id_pessoa = pac.id_pessoa
         ORDER BY p.nome
        """
    ))


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
          JOIN pessoa p      ON p.id_pessoa    = r.id_profissional
          JOIN atendimento a ON a.id_residente = r.id_profissional
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


@app.route("/api/analiticas/plantoes-por-residente")
def plantoes_por_residente():
    return jsonify(query(
        """
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
          JOIN pessoa p          ON p.id_pessoa       = r.id_profissional
          JOIN dia_para_isodow m ON m.dia_semana      = e.dia_semana
          JOIN dias_mes dm       ON dm.isodow         = m.isodow
         GROUP BY u.nome, p.nome
         ORDER BY u.nome, qtd_plantoes DESC
        """
    ))


if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv("PORT", "8000")))
