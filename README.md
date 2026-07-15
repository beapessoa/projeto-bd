# Hospital Universitário Dra. Yuska Maritan Brito

Sistema de gestão hospitalar para o Hospital Universitário Dra. Yuska Maritan Brito,
com controle de pacientes, profissionais (residentes e preceptores), atendimentos,
procedimentos, unidades e escalas de plantão.

Projeto acadêmico da disciplina de **Banco de Dados** — Etapa 1 (fundamentos):
modelagem conceitual, esquema físico, CRUD e consultas analíticas em **SQL puro**
(sem ORM), com uma interface web para demonstração.

## Autoras

- Beatriz Pessoa ([@beapessoa](https://github.com/beapessoa))
- Emyle Santos ([@Emysntts](https://github.com/Emysntts))

## Stack

- **Banco:** PostgreSQL 15+
- **Backend:** Python 3.10+ com Flask e `psycopg2` (SQL puro, sem ORM)
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
psql hospital_yuska -f sql/01_schema.sql   # cria tabelas e constraints
psql hospital_yuska -f sql/02_seed.sql     # popula dados de teste
```

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

sql/
  01_schema.sql       # CREATE TABLE de todas as entidades (com PK, FK, CHECK, NOT NULL, UNIQUE)
  02_seed.sql         # Dados de teste (15 pessoas, 4 unidades, 14 atendimentos, 16 procedimentos)
  03_crud.sql         # Consultas do requisito 3 (CRUD)
  04_analiticas.sql   # Consultas do requisito 4 (analíticas)

frontend/
  index.html          # Sidebar + páginas (dashboard, pacientes, atendimentos)
  css/style.css       # Tema escuro
  js/api.js           # Cliente HTTP genérico (get/post/put/del)
  js/app.js           # Roteamento entre páginas e handlers

app.py                # Servidor Flask (serve o frontend + endpoints /api/*)
requirements.txt      # Dependências Python
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
- Ver **procedimentos do atendimento** (query 3.3), com badge de nível de risco
- Adicionar procedimento realizado
- Remover procedimento — só permite se `faturado = FALSE` (query 3.5)
