"""
Concorrência com LOCK OTIMISTA (Etapa 2, requisito 6).

Rodar:  python -m orm.concorrencia_otimista
"""
import threading
import time

from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.exc import StaleDataError

from orm.db import SessionLocal
from orm.models import Escala, Preceptor

DEMORA_ENTRE_LER_E_ESCREVER = 0.15  # alarga a janela da corrida, para ela ser visível

_impressao = threading.Lock()
_inicio = 0.0


def log(transacao, mensagem):
    """Imprime com o tempo decorrido desde o início do cenário."""
    with _impressao:
        print(f"[{(time.monotonic() - _inicio) * 1000:6.0f} ms] {transacao}  {mensagem}")


def tentar_trocar_preceptor(nome, id_escala, novo_preceptor, barreira, resultados, usar_versao):
    """Uma transação trocando o preceptor do plantão. Roda em uma thread."""
    s = SessionLocal()
    barreira.wait()  
    log(nome, "início da transação")
    try:
        if usar_versao:
            # Caminho do ORM: o objeto carregado guarda o version_id lido.
            escala = s.get(Escala, id_escala)
            log(nome, f"leu a escala (preceptor={escala.id_preceptor}, "
                      f"version_id={escala.version_id})")
            time.sleep(DEMORA_ENTRE_LER_E_ESCREVER)

            escala.id_preceptor = novo_preceptor
            log(nome, f"vai gravar preceptor={novo_preceptor} "
                      f"(UPDATE ... WHERE version_id = {escala.version_id})")
            s.commit()
            log(nome, f"COMMIT ok — preceptor={novo_preceptor}, "
                      f"version_id agora é {escala.version_id}")
            resultados[nome] = "gravado"
        else:
            # Caminho sem controle de versão: UPDATE direto na tabela
            lido = s.execute(
                select(Escala.id_preceptor).where(Escala.id_escala == id_escala)
            ).scalar_one()
            log(nome, f"leu a escala (preceptor={lido})")
            time.sleep(DEMORA_ENTRE_LER_E_ESCREVER)

            log(nome, f"vai gravar preceptor={novo_preceptor} (UPDATE sem WHERE de versão)")
            s.execute(
                update(Escala.__table__)
                .where(Escala.__table__.c.id_escala == id_escala)
                .values(id_preceptor=novo_preceptor)
            )
            s.commit()
            log(nome, f"COMMIT ok — preceptor={novo_preceptor}")
            resultados[nome] = "gravado"

    except StaleDataError:
        s.rollback()
        log(nome, "CONFLITO DE VERSÃO: a linha mudou entre a leitura e o UPDATE "
                  "-> rollback, nada gravado")
        resultados[nome] = "conflito_versao"
    except SQLAlchemyError as exc:
        s.rollback()
        detalhe = str(getattr(exc, "orig", exc)).strip().splitlines()[0]
        log(nome, f"ERRO do banco: {detalhe}")
        resultados[nome] = "erro_banco"
    finally:
        s.close()


def estado_atual(id_escala):
    s = SessionLocal()
    try:
        escala = s.get(Escala, id_escala)
        return escala.id_preceptor, escala.version_id
    finally:
        s.close()


def rodar_cenario(titulo, id_escala, preceptores, usar_versao):
    global _inicio
    print(f"\n{'=' * 70}\n{titulo}\n{'=' * 70}")

    barreira = threading.Barrier(2)
    resultados = {}
    _inicio = time.monotonic()

    threads = [
        threading.Thread(target=tentar_trocar_preceptor,
                         args=(nome, id_escala, preceptor, barreira, resultados, usar_versao))
        for nome, preceptor in zip(("T1", "T2"), preceptores)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    preceptor_final, versao_final = estado_atual(id_escala)
    print(f"\nResultado: {resultados}")
    print(f"Estado final da escala: preceptor={preceptor_final}, version_id={versao_final}")
    return resultados


def escolher_cenario():
    """Pega uma escala qualquer e dois preceptores diferentes do atual, para disputar."""
    s = SessionLocal()
    try:
        escala = s.execute(select(Escala).order_by(Escala.id_escala).limit(1)).scalars().one()
        candidatos = s.execute(
            select(Preceptor.id_profissional)
            .where(Preceptor.id_profissional != escala.id_preceptor)
            .order_by(Preceptor.id_profissional)
            .limit(2)
        ).scalars().all()
        if len(candidatos) < 2:
            raise RuntimeError("São necessários pelo menos 3 preceptores para o teste.")
        return escala.id_escala, escala.id_preceptor, escala.version_id, tuple(candidatos)
    finally:
        s.close()


def restaurar(id_escala, id_preceptor, version_id):
    """Devolve a escala ao estado original, inclusive o version_id."""
    s = SessionLocal()
    try:
        s.execute(
            update(Escala.__table__)
            .where(Escala.__table__.c.id_escala == id_escala)
            .values(id_preceptor=id_preceptor, version_id=version_id)
        )
        s.commit()
    finally:
        s.close()


def main():
    id_escala, preceptor_original, versao_original, preceptores = escolher_cenario()
    print(f"Escala disputada: id_escala={id_escala} "
          f"(preceptor atual={preceptor_original}, version_id={versao_original})")
    print(f"T1 quer o preceptor {preceptores[0]}; T2 quer o preceptor {preceptores[1]}.")

    rodar_cenario(
        "CENÁRIO 1 — SEM CONTROLE DE VERSÃO: as duas gravam e uma escrita se perde",
        id_escala, preceptores, usar_versao=False,
    )
    print("Repare: ninguém recebeu erro, mas só um dos dois preceptores sobrou —")
    print("a escrita da outra transação foi sobrescrita em silêncio (lost update).")

    restaurar(id_escala, preceptor_original, versao_original)

    rodar_cenario(
        "CENÁRIO 2 — COM LOCK OTIMISTA: a segunda a commitar é barrada por versão",
        id_escala, preceptores, usar_versao=True,
    )
    print("Aqui a segunda transação foi avisada do conflito e desfez tudo:")
    print("o dado ficou consistente e a aplicação pode reler e tentar de novo.")

    restaurar(id_escala, preceptor_original, versao_original)
    print("\nEscala restaurada ao estado original.")


if __name__ == "__main__":
    main()
