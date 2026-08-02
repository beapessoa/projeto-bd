"""
Concorrência com LOCK PESSIMISTA (Etapa 2, requisito 6).

Cenário: duas transações tentam, ao mesmo tempo, escalar o MESMO residente para
a mesma unidade/dia/turno. A tabela ESCALA tem UNIQUE(id_unidade, dia_semana,
turno, id_residente), então o banco no fim das contas impede a duplicata — mas
depender só da constraint significa deixar a corrida acontecer e tratar o erro
depois. O objetivo aqui é impedir a corrida ANTES disso, com lock pessimista.

Qual linha travar? A escala ainda não existe (é ela que queremos inserir), então
não há o que travar nela. O recurso realmente disputado é o RESIDENTE — é ele que
não pode ser escalado duas vezes no mesmo lugar/horário. Então cada transação
trava a linha do residente com SELECT ... FOR UPDATE antes de verificar e inserir.

Rodar:  python -m orm.concorrencia_pessimista
"""
import threading
import time

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import lazyload

from orm.db import SessionLocal
from orm.models import Escala, Residente

DEMORA_ENTRE_LER_E_ESCREVER = 0.15  # alarga a janela da corrida, para ela ser visível

_impressao = threading.Lock()
_inicio = 0.0


def log(transacao, mensagem):
    """Imprime com o tempo decorrido desde o início do cenário."""
    with _impressao:
        print(f"[{(time.monotonic() - _inicio) * 1000:6.0f} ms] {transacao}  {mensagem}")


def travar_residente(s, id_residente):
    """
    SELECT ... FOR UPDATE na linha do residente.

    O lazyload é necessário porque Residente.profissional é eager "joined" no
    model: sem ele a query vira um LEFT OUTER JOIN, e o Postgres recusa
    FOR UPDATE sobre o lado anulável de um outer join.
    """
    return s.execute(
        select(Residente)
        .where(Residente.id_profissional == id_residente)
        .options(lazyload(Residente.profissional))
        .with_for_update()
    ).scalar_one()


def escala_existente(s, plantao):
    return s.execute(
        select(Escala).where(
            Escala.id_unidade == plantao["id_unidade"],
            Escala.dia_semana == plantao["dia_semana"],
            Escala.turno == plantao["turno"],
            Escala.id_residente == plantao["id_residente"],
        )
    ).scalars().first()


def tentar_escalar(nome, plantao, barreira, resultados, usar_lock):
    """Uma transação tentando criar a escala. Roda em uma thread."""
    s = SessionLocal()
    barreira.wait()  # as duas threads começam juntas
    log(nome, "início da transação")
    try:
        if usar_lock:
            pedido_em = time.monotonic()
            log(nome, f"pedindo LOCK no residente {plantao['id_residente']} (FOR UPDATE)...")
            travar_residente(s, plantao["id_residente"])
            espera = (time.monotonic() - pedido_em) * 1000
            log(nome, f"LOCK ADQUIRIDO (esperou {espera:.0f} ms)")

        # Esta releitura só enxerga o que a outra transação commitou porque o
        # Postgres roda em READ COMMITTED por padrão (cada comando tira um
        # snapshot novo). Em REPEATABLE READ a transação que esperou continuaria
        # com o snapshot antigo, não veria a escala recém-criada, tentaria
        # inserir e aí sim cairia na constraint UNIQUE.
        if escala_existente(s, plantao):
            log(nome, "verificou: a escala JÁ existe -> desiste sem erro")
            resultados[nome] = "recusado"
            s.rollback()
            return

        log(nome, "verificou: a escala não existe -> vai inserir")
        time.sleep(DEMORA_ENTRE_LER_E_ESCREVER)

        s.add(Escala(**plantao))
        s.commit()
        log(nome, "COMMIT ok — escala criada" + (", lock liberado" if usar_lock else ""))
        resultados[nome] = "criado"

    except IntegrityError as exc:
        s.rollback()
        restricao = getattr(getattr(exc.orig, "diag", None), "constraint_name", "?")
        log(nome, f"ERRO de integridade: constraint {restricao} violada")
        resultados[nome] = "erro_constraint"
    finally:
        s.close()


def rodar_cenario(titulo, plantao, usar_lock):
    global _inicio
    print(f"\n{'=' * 70}\n{titulo}\n{'=' * 70}")

    barreira = threading.Barrier(2)
    resultados = {}
    _inicio = time.monotonic()

    threads = [
        threading.Thread(target=tentar_escalar,
                         args=(nome, plantao, barreira, resultados, usar_lock))
        for nome in ("T1", "T2")
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    print(f"\nResultado: {resultados}")
    return resultados


def escolher_plantao_livre(s):
    """Acha uma combinação unidade+dia+turno+residente que ainda não existe."""
    residente = s.execute(select(Residente).limit(1)).scalars().one()
    ocupados = {
        (e.id_unidade, e.dia_semana, e.turno)
        for e in s.execute(
            select(Escala).where(Escala.id_residente == residente.id_profissional)
        ).scalars()
    }
    alguma_escala = s.execute(select(Escala).limit(1)).scalars().one()
    for dia in ("Segunda", "Terca", "Quarta", "Quinta", "Sexta", "Sabado", "Domingo"):
        for turno in ("Manha", "Tarde", "Noite"):
            if (alguma_escala.id_unidade, dia, turno) not in ocupados:
                return {
                    "id_unidade": alguma_escala.id_unidade,
                    "dia_semana": dia,
                    "turno": turno,
                    "id_residente": residente.id_profissional,
                    "id_preceptor": alguma_escala.id_preceptor,
                }
    raise RuntimeError("Nenhum horário livre para o teste.")


def limpar(plantao):
    s = SessionLocal()
    try:
        for escala in s.execute(
            select(Escala).where(
                Escala.id_unidade == plantao["id_unidade"],
                Escala.dia_semana == plantao["dia_semana"],
                Escala.turno == plantao["turno"],
                Escala.id_residente == plantao["id_residente"],
            )
        ).scalars():
            s.delete(escala)
        s.commit()
    finally:
        s.close()


def main():
    s = SessionLocal()
    try:
        plantao = escolher_plantao_livre(s)
    finally:
        s.close()

    print(f"Plantão disputado pelas duas transações: {plantao}")

    limpar(plantao)
    rodar_cenario(
        "CENÁRIO 1 — SEM LOCK: a corrida acontece e o banco rejeita na marra",
        plantao, usar_lock=False,
    )

    limpar(plantao)
    rodar_cenario(
        "CENÁRIO 2 — COM LOCK PESSIMISTA: a corrida é impedida antes da constraint",
        plantao, usar_lock=True,
    )

    limpar(plantao)
    print("\nDados de teste removidos.")


if __name__ == "__main__":
    main()
