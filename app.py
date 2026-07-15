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


if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv("PORT", "8000")))
