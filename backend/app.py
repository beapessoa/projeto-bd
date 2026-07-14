import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from db import get_connection

app = Flask(__name__)
CORS(app)


# ---- Pacientes ----

@app.route("/api/pacientes", methods=["GET"])
def listar_pacientes():
    # TODO
    return jsonify([])


@app.route("/api/pacientes", methods=["POST"])
def criar_paciente():
    # TODO
    return jsonify({"msg": "não implementado"}), 501


@app.route("/api/pacientes/<int:id_pessoa>", methods=["PUT"])
def atualizar_paciente(id_pessoa):
    # TODO
    return jsonify({"msg": "não implementado"}), 501


# ---- Profissionais ----

@app.route("/api/profissionais", methods=["GET"])
def listar_profissionais():
    # TODO
    return jsonify([])


@app.route("/api/residentes", methods=["GET"])
def listar_residentes():
    # TODO
    return jsonify([])


@app.route("/api/preceptores", methods=["GET"])
def listar_preceptores():
    # TODO
    return jsonify([])


# ---- Atendimentos ----

@app.route("/api/atendimentos", methods=["GET"])
def listar_atendimentos():
    # TODO
    return jsonify([])


@app.route("/api/atendimentos", methods=["POST"])
def criar_atendimento():
    # TODO
    return jsonify({"msg": "não implementado"}), 501


@app.route("/api/atendimentos/<int:id_atendimento>/procedimentos", methods=["GET"])
def listar_procedimentos_atendimento(id_atendimento):
    # TODO
    return jsonify([])


# ---- Procedimentos ----

@app.route("/api/procedimentos", methods=["GET"])
def listar_procedimentos():
    # TODO
    return jsonify([])


@app.route("/api/procedimentos-realizados", methods=["POST"])
def registrar_procedimento_realizado():
    # TODO
    return jsonify({"msg": "não implementado"}), 501


@app.route("/api/procedimentos-realizados", methods=["DELETE"])
def remover_procedimento_realizado():
    # TODO
    return jsonify({"msg": "não implementado"}), 501


# ---- Unidades e Escalas ----

@app.route("/api/unidades", methods=["GET"])
def listar_unidades():
    # TODO
    return jsonify([])


@app.route("/api/escalas", methods=["GET"])
def listar_escalas():
    # TODO
    return jsonify([])


@app.route("/api/escalas", methods=["POST"])
def criar_escala():
    # TODO
    return jsonify({"msg": "não implementado"}), 501


# ---- Consultas analíticas ----

@app.route("/api/analiticas/ranking-residentes", methods=["GET"])
def ranking_residentes():
    # TODO
    return jsonify([])


@app.route("/api/analiticas/preceptores-ativos", methods=["GET"])
def preceptores_ativos():
    # TODO
    return jsonify([])


@app.route("/api/analiticas/plantoes-por-residente", methods=["GET"])
def plantoes_por_residente():
    # TODO
    return jsonify([])


@app.route("/api/analiticas/pacientes-sem-risco-alto", methods=["GET"])
def pacientes_sem_risco_alto():
    # TODO
    return jsonify([])


if __name__ == "__main__":
    app.run(debug=True, port=5000)
