# Hospital Universitário Dra. Yuska Maritan Brito

Sistema de gestão hospitalar para o Hospital Universitário Dra. Yuska Maritan Brito,
com controle de pacientes, profissionais (residentes e preceptores), atendimentos,
procedimentos, unidades e escalas de plantão.

Projeto acadêmico da disciplina de **Banco de Dados**, em duas etapas:

- **Etapa 1 (fundamentos):** modelagem conceitual, esquema físico, CRUD e consultas
  analíticas em SQL puro, com uma interface web para demonstração.
- **Etapa 2 (funcionalidades avançadas):** stored procedures, triggers, views,
  migração da aplicação para **ORM (SQLAlchemy)**, consultas avançadas e tratamento
  de concorrência. Todas essas funcionalidades também aparecem na interface.

## Autoras

- Beatriz Pessoa ([@beapessoa](https://github.com/beapessoa))
- Emyle Santos ([@Emysntts](https://github.com/Emysntts))

## Stack

- **Banco:** PostgreSQL 15+
- **Backend:** Python 3.10+ com Flask e **SQLAlchemy** (na Etapa 1 era `psycopg2`
  com SQL puro; a Etapa 2 migrou tudo para ORM)
- **Frontend:** HTML + CSS + JavaScript puro, servido pelo próprio Flask

## Pré-requisitos

- PostgreSQL 15+ rodando localmente (`brew install postgresql@17` no macOS)
- Python 3.10+

## Instalação e execução

### 1. Clone e entre no projeto

```bash
git clone git@github.com:beapessoa/projeto-bd.git
cd projeto-bd
```

### 2. Crie o banco e rode os scripts

```bash
createdb hospital_yuska
psql hospital_yuska -f sql/01_schema.sql        # cria tabelas e constraints
psql hospital_yuska -f sql/02_seed.sql          # popula dados de teste
psql hospital_yuska -f sql/05_procedures.sql    # stored procedures (Etapa 2)
psql hospital_yuska -f sql/06_triggers.sql      # triggers (Etapa 2)
psql hospital_yuska -f sql/07_views.sql         # views (Etapa 2)
psql hospital_yuska -f sql/08_concorrencia.sql  # coluna version_id (lock otimista)
```

Rode na ordem: alguns scripts da Etapa 2 acrescentam colunas que os anteriores
usam. O `08` é obrigatório para o app subir — o model `Escala` mapeia `version_id`.

### 3. Configure o ambiente Python

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Rode o servidor

```bash
python app.py
```

Abra **<http://localhost:8000>** no navegador. O Flask serve o backend
(`/api/*`) e o frontend na mesma porta.

### Variáveis de ambiente (opcionais)

Se seu Postgres não usa as configurações padrão:

| Variável | Padrão |
|---|---|
| `DB_HOST` | `localhost` |
| `DB_PORT` | `5432` |
| `DB_NAME` | `hospital_yuska` |
| `DB_USER` | seu usuário do sistema |
| `DB_PASSWORD` | vazia |
| `PORT` | `8000` |

## Estrutura do projeto

```
docs/
  modelo_conceitual.pdf                    # DER + justificativas (cardinalidades, especialização)
  modelo_conceitual.png                    # DER (imagem solta)
  modelo_relacional _e_normalizacao.pdf    # Modelo relacional + normalização 3FN
  modelo_relacional.png                    # Diagrama relacional (imagem solta)
  relatorio_etapa2.pdf                     # Relatório de decisões da Etapa 2 (entrega final)
  relatorio_etapa2.md                      # Fonte do relatório, em Markdown

sql/
  01_schema.sql       # CREATE TABLE de todas as entidades (com PK, FK, CHECK, NOT NULL, UNIQUE)
  02_seed.sql         # Dados de teste (15 pessoas, 4 unidades, 14 atendimentos, 16 procedimentos)
  03_crud.sql         # Consultas do requisito 3 (CRUD) — Etapa 1
  04_analiticas.sql   # Consultas do requisito 4 (analíticas) — Etapa 1
  05_procedures.sql   # Stored procedures (Etapa 2)
  06_triggers.sql     # Triggers + tabela auditoria_atendimento (Etapa 2)
  07_views.sql        # Views + tabela internacao (Etapa 2)
  08_concorrencia.sql # Coluna version_id em escala, para o lock otimista (Etapa 2)

orm/                  # Etapa 2 — camada de ORM
  db.py                      # Engine + sessionmaker (mesmas variáveis de ambiente)
  models.py                  # Mapeamento das entidades, com lazy/eager comentados
  consultas_avancadas.py     # Consultas do requisito 5, na DSL do SQLAlchemy
  concorrencia_pessimista.py # Demo de lock pessimista (SELECT ... FOR UPDATE)
  concorrencia_otimista.py   # Demo de lock otimista (version_id)

frontend/
  index.html          # Topnav + páginas (dashboard, cadastros, atendimentos, Etapa 2)
  css/style.css       # Estilos
  js/api.js           # Cliente HTTP genérico (get/post/put/del)
  js/app.js           # Roteamento entre páginas e handlers

app.py                # Servidor Flask (serve o frontend + endpoints /api/*)
requirements.txt      # Dependências Python
```

## Demonstrações por linha de comando (Etapa 2)

As duas demos de concorrência rodam fora da interface, porque precisam de duas
transações simultâneas com log da ordem de execução:

```bash
python -m orm.concorrencia_pessimista
```

```bash
python -m orm.concorrencia_otimista
```

As consultas avançadas também podem ser vistas no terminal (na interface elas
ficam na aba **Consultas**):

```bash
python -m orm.consultas_avancadas
```

## Funcionalidades da interface

### Dashboard
- Totais gerais (pacientes, residentes, preceptores, atendimentos)
- Tempo médio de atendimento por residente (query 3.6)
- **Ranking de residentes por número de atendimentos** (query 4.1)
- **Preceptores com mais de 5 atendimentos no mês** — com filtro dinâmico de mês (query 4.2)
- **Plantões por residente e unidade no mês corrente** (query 4.3)
- Lista dos últimos atendimentos

### Pacientes
- Listagem com alergias em badges
- Cadastrar novo paciente
- Editar (endereço, convênio, grupo sanguíneo, alergias) — usa a query 3.4

### Atendimentos
- Listagem completa (data, paciente, residente, preceptor, duração)
- **Novo atendimento** com validação de existência das FKs (query 3.1)
- Ao adicionar procedimentos já no formulário de novo atendimento, o registro passa
  pela procedure **`sp_registrar_atendimento_completo`**, numa única transação
- Ver **procedimentos do atendimento** (query 3.3), com badge de nível de risco
- Adicionar procedimento realizado
- Remover procedimento — só permite se `faturado = FALSE` (query 3.5)

### Escalas
- Listagem com filtros por unidade, dia e turno
- Criar escala — a tentativa de escalar o mesmo residente no mesmo dia/turno em
  outra unidade é barrada pelo trigger **`trg_check_sobreposicao_escala`**, e o
  motivo aparece na tela
- **Reajustar escalas**: move todos os plantões de um residente de um dia/turno
  para outro, pela procedure **`sp_reajustar_escala`**

### Internações (Etapa 2)
- Quem está internado agora, a partir da view **`vw_pacientes_internados`**
- Registrar nova internação e dar alta
- Histórico completo, com o status de cada internação

### Análises (Etapa 2)
- **Tempo médio de espera por unidade** — procedure `sp_calcular_tempo_medio_espera`
- **Residentes sem supervisão adequada** — view `vw_residentes_sem_supervisor`
- **Estatísticas mensais de atendimentos** — view `vw_estatisticas_atendimentos_mensal`
- **Catálogo de procedimentos** comparando o tempo previsto com a média realizada,
  que é mantida pelo trigger `trg_atualiza_media_procedimentos`

### Consultas avançadas (Etapa 2, requisito 5)
Todas montadas com a DSL do SQLAlchemy, sem SQL cru:
- Preceptores que supervisionaram atendimentos a pacientes flamenguistas
- Percentual de procedimentos de alto risco por residente
- Último atendimento de cada paciente, com residente, preceptor e procedimentos

### Auditoria (Etapa 2)
- Trilha de INSERT/UPDATE/DELETE em atendimentos, gravada pelo trigger
  **`trg_audita_atendimento`**
- Em um UPDATE, mostra apenas os campos que mudaram, com valor antigo e novo
- Começa vazia num banco recém-criado: crie ou edite um atendimento para ver o
  trigger agindo
