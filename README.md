# Hospital Universitário Dra. Yuska Maritan Brito

Sistema de gestão hospitalar para controle de atendimentos, profissionais, pacientes, procedimentos, internações e escalas de plantão.

## Pré-requisitos

- PostgreSQL 15+
- Python 3.10+

## Setup

### Banco de dados

```bash
createdb hospital_yuska
psql hospital_yuska < sql/01_schema.sql
psql hospital_yuska < sql/02_seed.sql
```

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

O servidor sobe em `http://localhost:5000`.

### Frontend

Abra `frontend/index.html` no navegador (ou use Live Server no VS Code).

## Estrutura

```
sql/
  01_schema.sql       -- Criação das tabelas
  02_seed.sql         -- Dados de teste
  03_crud.sql         -- Consultas CRUD
  04_analiticas.sql   -- Consultas analíticas
backend/
  app.py              -- API Flask
  db.py               -- Conexão com PostgreSQL
  requirements.txt
frontend/
  index.html
  css/style.css
  js/api.js           -- Cliente HTTP
  js/app.js           -- Lógica da interface
```
