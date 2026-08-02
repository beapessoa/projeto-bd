"""
Consultas avançadas via ORM (Etapa 2, requisito 5).

Todas montadas com a DSL do SQLAlchemy — nenhuma string de SQL cru. Cada função
recebe uma Session e devolve uma lista de dicts.

Rodar:  python -m orm.consultas_avancadas
"""
from sqlalchemy import case, distinct, func, literal
from sqlalchemy.orm import aliased

from orm.db import SessionLocal
from orm.models import (
    Atendimento, Paciente, Pessoa, Preceptor, Procedimento, ProcedimentoRealizado,
    Residente,
)


def preceptores_de_pacientes_flamenguistas(s):
    """
    Preceptores que supervisionaram residentes em atendimentos a pacientes
    flamenguistas. O vínculo de supervisão é o próprio atendimento, que já traz
    residente e preceptor na mesma linha.
    """
    # Três aliases de Pessoa: preceptor, residente e paciente saem todos da mesma
    # tabela, então sem alias o SQLAlchemy não saberia qual JOIN é qual.
    pessoa_preceptor = aliased(Pessoa)
    pessoa_residente = aliased(Pessoa)
    pessoa_paciente = aliased(Pessoa)

    qtd_atendimentos = func.count(distinct(Atendimento.id_atendimento))
    residentes = func.string_agg(distinct(pessoa_residente.nome), literal(", "))

    linhas = (
        s.query(
            Preceptor.id_profissional,
            pessoa_preceptor.nome,
            Preceptor.titulacao,
            qtd_atendimentos,
            residentes,
        )
        .select_from(Atendimento)
        .join(Preceptor, Preceptor.id_profissional == Atendimento.id_preceptor)
        .join(pessoa_preceptor, pessoa_preceptor.id_pessoa == Preceptor.id_profissional)
        .join(Residente, Residente.id_profissional == Atendimento.id_residente)
        .join(pessoa_residente, pessoa_residente.id_pessoa == Residente.id_profissional)
        .join(Paciente, Paciente.id_pessoa == Atendimento.id_paciente)
        .join(pessoa_paciente, pessoa_paciente.id_pessoa == Paciente.id_pessoa)
        .filter(pessoa_paciente.is_flamengo.is_(True))
        .group_by(Preceptor.id_profissional, pessoa_preceptor.nome, Preceptor.titulacao)
        .order_by(qtd_atendimentos.desc(), pessoa_preceptor.nome)
        .all()
    )

    return [
        {
            "id_preceptor": id_preceptor,
            "preceptor": nome,
            "titulacao": titulacao,
            "qtd_atendimentos": qtd,
            "residentes_supervisionados": nomes_residentes,
        }
        for id_preceptor, nome, titulacao, qtd, nomes_residentes in linhas
    ]


def percentual_risco_alto_por_residente(s):
    """
    Percentual de procedimentos de risco ALTO sobre o total de procedimentos que
    cada residente realizou. Conta registros de procedimento_realizado, não a
    coluna quantidade — o que importa é quantas vezes o procedimento aconteceu.
    """
    total = func.count(ProcedimentoRealizado.id_procedimento)
    alto = func.count(case((Procedimento.nivel_risco == "ALTO", 1)))

    # nullif evita divisão por zero: residente sem nenhum procedimento fica com
    # percentual NULL (que é diferente de ter 0% de risco alto).
    percentual = func.round(100.0 * alto / func.nullif(total, 0), 2)

    linhas = (
        s.query(Residente.id_profissional, Pessoa.nome, Residente.ano_residencia,
                total, alto, percentual)
        .select_from(Residente)
        .join(Pessoa, Pessoa.id_pessoa == Residente.id_profissional)
        .outerjoin(Atendimento, Atendimento.id_residente == Residente.id_profissional)
        .outerjoin(ProcedimentoRealizado,
                   ProcedimentoRealizado.id_atendimento == Atendimento.id_atendimento)
        .outerjoin(Procedimento,
                   Procedimento.id_procedimento == ProcedimentoRealizado.id_procedimento)
        .group_by(Residente.id_profissional, Pessoa.nome, Residente.ano_residencia)
        .order_by(percentual.desc().nullslast(), Pessoa.nome)
        .all()
    )

    return [
        {
            "id_residente": id_residente,
            "residente": nome,
            "ano_residencia": ano,
            "total_procedimentos": total_,
            "procedimentos_risco_alto": alto_,
            "percentual_risco_alto": float(pct) if pct is not None else None,
        }
        for id_residente, nome, ano, total_, alto_, pct in linhas
    ]


def main():
    s = SessionLocal()
    try:
        print("\n=== Preceptores que supervisionaram atendimentos a pacientes flamenguistas ===")
        for linha in preceptores_de_pacientes_flamenguistas(s):
            print(f"  {linha['preceptor']} ({linha['titulacao']}) — "
                  f"{linha['qtd_atendimentos']} atendimento(s); "
                  f"residentes: {linha['residentes_supervisionados']}")

        print("\n=== Percentual de procedimentos de risco ALTO por residente ===")
        for linha in percentual_risco_alto_por_residente(s):
            pct = linha["percentual_risco_alto"]
            pct_txt = "sem procedimentos" if pct is None else f"{pct:.2f}%"
            print(f"  {linha['residente']} ({linha['ano_residencia']}) — "
                  f"{linha['procedimentos_risco_alto']}/{linha['total_procedimentos']} "
                  f"= {pct_txt}")
    finally:
        s.close()


if __name__ == "__main__":
    main()
