// ============================================================
// Opções fixas dos formulários
// ============================================================
const GRUPOS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"];
const DIAS = ["Segunda", "Terca", "Quarta", "Quinta", "Sexta", "Sabado", "Domingo"];
const TURNOS = ["Manha", "Tarde", "Noite"];
const TIPOS_UNIDADE = ["Enfermaria", "UTI", "Pronto-Socorro", "Ambulatorio"];
const ANOS_RES = ["R1", "R2", "R3"];
const TITULACOES = ["Especialista", "Mestre", "Doutor", "Pos-Doutor", "Livre-Docente"];
let atendimentosCache = [];
let atendimentoAtual = null;

// ============================================================
// Configuração de cada entidade (colunas da tabela + campos do form).
// campo.novo = aparece só no cadastro; campo.de = <select> vindo de outra API.
// ============================================================
const ENT = {
    pacientes: {
        titulo: "Pacientes", singular: "Paciente", endpoint: "/pacientes", id: "id_pessoa",
        colunas: [
            ["Nome", (r) => esc(r.nome)],
            ["CPF", (r) => esc(r.cpf)],
            ["Convênio", (r) => esc(r.num_convenio || "—")],
            ["Grupo", (r) => esc(r.grupo_sanguineo)],
            ["Endereço", (r) => esc(r.endereco || "—")],
            ["Alergias", (r) => badges(r.alergias)],
        ],
        campos: [
            { k: "nome", label: "Nome", req: true, novo: true },
            { k: "cpf", label: "CPF (11 dígitos)", req: true, novo: true },
            { k: "data_nascimento", label: "Nascimento", type: "date", req: true, novo: true },
            { k: "telefone", label: "Telefone", req: true, novo: true },
            { k: "is_flamengo", label: "Torce pro Flamengo", type: "checkbox", novo: true },
            { k: "grupo_sanguineo", label: "Grupo sanguíneo", type: "select", opcoes: GRUPOS, req: true },
            { k: "num_convenio", label: "Convênio" },
            { k: "endereco", label: "Endereço" },
            { k: "alergias", label: "Alergias (separadas por vírgula)", type: "csv" },
        ],
    },
    residentes: {
        titulo: "Residentes", singular: "Residente", endpoint: "/residentes", id: "id_pessoa",
        colunas: [
            ["Nome", (r) => esc(r.nome)],
            ["CRM", (r) => esc(r.crm)],
            ["Especialidade", (r) => esc(r.especialidade)],
            ["Ano", (r) => esc(r.ano_residencia)],
            ["Telefone", (r) => esc(r.telefone)],
        ],
        campos: [
            { k: "nome", label: "Nome", req: true, novo: true },
            { k: "cpf", label: "CPF (11 dígitos)", req: true, novo: true },
            { k: "data_nascimento", label: "Nascimento", type: "date", req: true, novo: true },
            { k: "telefone", label: "Telefone", req: true },
            { k: "crm", label: "CRM", req: true },
            { k: "data_admissao", label: "Admissão", type: "date", req: true, novo: true },
            { k: "especialidade", label: "Especialidade", req: true },
            { k: "ano_residencia", label: "Ano de residência", type: "select", opcoes: ANOS_RES, req: true },
        ],
    },
    preceptores: {
        titulo: "Preceptores", singular: "Preceptor", endpoint: "/preceptores", id: "id_pessoa",
        colunas: [
            ["Nome", (r) => esc(r.nome)],
            ["CRM", (r) => esc(r.crm)],
            ["Especialidade", (r) => esc(r.especialidade)],
            ["Titulação", (r) => esc(r.titulacao)],
            ["Telefone", (r) => esc(r.telefone)],
        ],
        campos: [
            { k: "nome", label: "Nome", req: true, novo: true },
            { k: "cpf", label: "CPF (11 dígitos)", req: true, novo: true },
            { k: "data_nascimento", label: "Nascimento", type: "date", req: true, novo: true },
            { k: "telefone", label: "Telefone", req: true },
            { k: "crm", label: "CRM", req: true },
            { k: "data_admissao", label: "Admissão", type: "date", req: true, novo: true },
            { k: "especialidade", label: "Especialidade", req: true },
            { k: "titulacao", label: "Titulação", type: "select", opcoes: TITULACOES, req: true },
        ],
    },
    unidades: {
        titulo: "Unidades", singular: "Unidade", endpoint: "/unidades", id: "id_unidade",
        colunas: [
            ["Nome", (r) => esc(r.nome)],
            ["Tipo", (r) => esc(r.tipo)],
            ["Leitos", (r) => r.capacidade_leitos],
        ],
        campos: [
            { k: "nome", label: "Nome", req: true },
            { k: "tipo", label: "Tipo", type: "select", opcoes: TIPOS_UNIDADE, req: true },
            { k: "capacidade_leitos", label: "Capacidade de leitos", type: "number", req: true },
        ],
    },
    escalas: {
        titulo: "Escalas", singular: "Escala", endpoint: "/escalas", id: "id_escala", semEdicao: true,
        filtros: [
            { k: "unidade", label: "Unidade", de: { endpoint: "/unidades", val: "id_unidade", txt: "nome" } },
            { k: "dia", label: "Dia", opcoes: DIAS },
            { k: "turno", label: "Turno", opcoes: TURNOS },
        ],
        colunas: [
            ["Unidade", (r) => esc(r.unidade)],
            ["Dia", (r) => esc(r.dia_semana)],
            ["Turno", (r) => esc(r.turno)],
            ["Residente", (r) => esc(r.residente)],
            ["Preceptor", (r) => esc(r.preceptor)],
        ],
        campos: [
            { k: "id_unidade", label: "Unidade", type: "select", req: true, de: { endpoint: "/unidades", val: "id_unidade", txt: "nome" } },
            { k: "dia_semana", label: "Dia", type: "select", opcoes: DIAS, req: true },
            { k: "turno", label: "Turno", type: "select", opcoes: TURNOS, req: true },
            { k: "id_residente", label: "Residente", type: "select", req: true, de: { endpoint: "/residentes", val: "id_pessoa", txt: "nome" } },
            { k: "id_preceptor", label: "Preceptor", type: "select", req: true, de: { endpoint: "/preceptores", val: "id_pessoa", txt: "nome" } },
        ],
    },
};

// Quais painéis cada página do menu mostra.
const PAGINAS = {
    pacientes: ["pacientes"],
    profissionais: ["residentes", "preceptores"],
    unidades: ["unidades"],
    escalas: ["escalas"],
};

// ============================================================
// Roteamento
// ============================================================
document.addEventListener("DOMContentLoaded", () => {
    const navLinks = document.querySelectorAll(".nav-link");
    const pageTitle = document.getElementById("page-title");

    navLinks.forEach((link) => {
        link.addEventListener("click", (e) => {
            e.preventDefault();
            navLinks.forEach((l) => l.classList.remove("active"));
            link.classList.add("active");
            pageTitle.textContent = link.textContent;
            showPage(link.dataset.page);
        });
    });

    document.getElementById("modal-cancel").addEventListener("click", fecharModal);
    document.getElementById("modal").addEventListener("click", (e) => {
        if (e.target.id === "modal") fecharModal();
    });
    document.getElementById("modal-form").addEventListener("submit", salvarModal);

    setupAtendimentoModal();
    setupProcedimentosModal();
    setupFiltroPreceptores();
    showPage("dashboard");
});

function showPage(page) {
    document.querySelectorAll(".page").forEach((s) => (s.hidden = true));
    if (page === "dashboard") {
        document.getElementById("page-dashboard").hidden = false;
        loadDashboard();
        return;
    }
    if (page === "atendimentos") {
        document.getElementById("page-atendimentos").hidden = false;
        loadAtendimentos();
        return;
    }
    const cont = document.getElementById("page-entidades");
    cont.hidden = false;
    cont.innerHTML = PAGINAS[page].map(panelHtml).join("");
    PAGINAS[page].forEach(setupPanel);
}

// ============================================================
// Dashboard
// ============================================================
async function loadDashboard() {
    try {
        const s = await api.get("/stats");
        document.getElementById("stat-pacientes").textContent = s.pacientes;
        document.getElementById("stat-residentes").textContent = s.residentes;
        document.getElementById("stat-preceptores").textContent = s.preceptores;
        document.getElementById("stat-atendimentos").textContent = s.atendimentos;
    } catch (_) {
        toast("Não consegui falar com a API. Ela está rodando?", "error");
    }
    renderTabela("/tempo-medio-residente", "tabela-tempo-medio", 3, (d) =>
        `<td>${esc(d.residente)}</td><td>${d.qtd_atendimentos}</td><td>${d.tempo_medio_minutos}</td>`
    );

    let pos = 0;
    renderTabela("/analiticas/ranking-residentes", "tabela-ranking-residentes", 3, (d) =>
        `<td>${++pos}º</td><td>${esc(d.residente)}</td><td>${d.total_atendimentos}</td>`
    );

    renderTabela("/analiticas/plantoes-por-residente", "tabela-plantoes", 3, (d) =>
        `<td>${esc(d.unidade)}</td><td>${esc(d.residente)}</td><td>${d.qtd_plantoes}</td>`
    );

    renderTabela("/atendimentos-recentes", "tabela-atendimentos", 5, (a) =>
        `<td>${esc(a.data_hora)}</td><td>${esc(a.paciente)}</td><td>${esc(a.residente)}</td>` +
        `<td>${esc(a.preceptor)}</td><td>${a.duracao_minutos}</td>`
    );
}

// ---- Filtro de preceptores ativos (4.2) ----
function setupFiltroPreceptores() {
    const input = document.getElementById("filtro-mes-preceptores");
    const hoje = new Date();
    input.value = `${hoje.getFullYear()}-${String(hoje.getMonth() + 1).padStart(2, "0")}`;
    input.addEventListener("change", carregarPreceptoresAtivos);
    carregarPreceptoresAtivos();
}

async function carregarPreceptoresAtivos() {
    const valor = document.getElementById("filtro-mes-preceptores").value;
    if (!valor) return;
    const [ano, mes] = valor.split("-");
    const tbody = document.getElementById("tabela-preceptores-ativos");
    try {
        const dados = await api.get(`/analiticas/preceptores-ativos?ano=${ano}&mes=${Number(mes)}`);
        tbody.innerHTML = dados.length
            ? dados.map((d) =>
                `<tr><td>${esc(d.preceptor)}</td><td>${d.total_atendimentos}</td></tr>`
              ).join("")
            : `<tr><td colspan="2" class="empty">Nenhum preceptor com mais de 5 atendimentos.</td></tr>`;
    } catch (_) {
        tbody.innerHTML = `<tr><td colspan="2" class="empty">Erro ao carregar.</td></tr>`;
    }
}

async function renderTabela(path, tbodyId, cols, rowHtml) {
    const tbody = document.getElementById(tbodyId);
    try {
        const dados = await api.get(path);
        tbody.innerHTML = dados.length
            ? dados.map((d) => `<tr>${rowHtml(d)}</tr>`).join("")
            : `<tr><td colspan="${cols}" class="empty">Sem dados.</td></tr>`;
    } catch (_) {
        tbody.innerHTML = `<tr><td colspan="${cols}" class="empty">Erro ao carregar.</td></tr>`;
    }
}

// ============================================================
// Painéis de cadastro (listagem + Novo + Editar)
// ============================================================
function panelHtml(k) {
    const e = ENT[k];
    const ths = e.colunas.map((c) => `<th>${c[0]}</th>`).join("") + (e.semEdicao ? "" : "<th></th>");
    const nCols = e.colunas.length + (e.semEdicao ? 0 : 1);
    const filtros = e.filtros
        ? `<div class="filtros" data-filtros="${k}">${e.filtros.map((f) =>
              `<select data-filtro="${f.k}"><option value="">${esc(f.label)}: todos</option>` +
              (f.opcoes || []).map((o) => `<option value="${esc(o)}">${esc(o)}</option>`).join("") +
              `</select>`).join("")}</div>`
        : "";
    return `<div class="table-container" style="margin-bottom:24px;">
        <div class="panel-head">
            <h3>${e.titulo}</h3>
            <button class="btn btn-primary btn-sm" data-novo="${k}">+ Novo</button>
        </div>
        ${filtros}
        <table>
            <thead><tr>${ths}</tr></thead>
            <tbody data-tbody="${k}">
                <tr><td colspan="${nCols}" class="empty">Carregando...</td></tr>
            </tbody>
        </table>
    </div>`;
}

async function setupPanel(k) {
    const e = ENT[k];
    document.querySelector(`[data-novo="${k}"]`).addEventListener("click", () => abrirModal(k, null));
    if (e.filtros) {
        const box = document.querySelector(`[data-filtros="${k}"]`);
        for (const f of e.filtros.filter((f) => f.de)) {
            await preencherSelect(box.querySelector(`[data-filtro="${f.k}"]`), f.de, `${f.label}: todos`);
        }
        box.querySelectorAll("[data-filtro]").forEach((sel) =>
            sel.addEventListener("change", () => loadPanel(k))
        );
    }
    loadPanel(k);
}

async function loadPanel(k) {
    const e = ENT[k];
    const tbody = document.querySelector(`[data-tbody="${k}"]`);
    const nCols = e.colunas.length + (e.semEdicao ? 0 : 1);
    let url = e.endpoint;
    if (e.filtros) {
        const box = document.querySelector(`[data-filtros="${k}"]`);
        const qs = [];
        box.querySelectorAll("[data-filtro]").forEach((sel) => {
            if (sel.value) qs.push(`${sel.dataset.filtro}=${encodeURIComponent(sel.value)}`);
        });
        if (qs.length) url += "?" + qs.join("&");
    }
    try {
        const dados = await api.get(url);
        if (!dados.length) {
            tbody.innerHTML = `<tr><td colspan="${nCols}" class="empty">Nenhum registro.</td></tr>`;
            return;
        }
        tbody.innerHTML = dados.map((r) => linhaHtml(k, r)).join("");
        if (!e.semEdicao) {
            tbody.querySelectorAll("[data-editar]").forEach((btn) =>
                btn.addEventListener("click", () =>
                    abrirModal(k, dados.find((r) => String(r[e.id]) === btn.dataset.id))
                )
            );
        }
    } catch (_) {
        tbody.innerHTML = `<tr><td colspan="${nCols}" class="empty">Erro ao carregar (a API está no ar?).</td></tr>`;
    }
}

function linhaHtml(k, r) {
    const e = ENT[k];
    const tds = e.colunas.map((c) => `<td>${c[1](r)}</td>`).join("");
    const acao = e.semEdicao
        ? ""
        : `<td><button class="btn btn-primary btn-sm" data-editar data-id="${esc(r[e.id])}">Editar</button></td>`;
    return `<tr>${tds}${acao}</tr>`;
}

// ============================================================
// Modal genérico (cadastro / edição)
// ============================================================
async function abrirModal(k, registro) {
    const e = ENT[k];
    const editando = !!registro;
    const campos = e.campos.filter((c) => !(editando && c.novo));
    const form = document.getElementById("modal-form");
    form.dataset.ent = k;
    form.dataset.id = editando ? registro[e.id] : "";
    document.getElementById("modal-title").textContent = (editando ? "Editar " : "Novo ") + e.singular;
    document.getElementById("modal-fields").innerHTML = campos.map((c) => campoHtml(c, registro)).join("");

    for (const c of campos.filter((c) => c.de)) {
        const sel = document.getElementById("f-" + c.k);
        await preencherSelect(sel, c.de, "Selecione...");
        if (editando && registro[c.k] != null) sel.value = registro[c.k];
    }
    document.getElementById("modal").classList.add("open");
}

function campoHtml(c, registro) {
    const val = registro ? registro[c.k] : undefined;
    const id = "f-" + c.k;
    let input;
    if (c.type === "select" && !c.de) {
        input = `<select id="${id}"><option value="">Selecione...</option>` +
            c.opcoes.map((o) => `<option value="${esc(o)}" ${val === o ? "selected" : ""}>${esc(o)}</option>`).join("") +
            `</select>`;
    } else if (c.type === "select") {
        input = `<select id="${id}"><option value="">Selecione...</option></select>`;
    } else if (c.type === "checkbox") {
        input = `<input type="checkbox" id="${id}" ${val ? "checked" : ""} style="width:auto;">`;
    } else if (c.type === "csv") {
        const v = Array.isArray(val) ? val.join(", ") : "";
        input = `<input type="text" id="${id}" value="${esc(v)}" placeholder="ex.: Dipirona, Penicilina">`;
    } else {
        const t = c.type === "number" ? "number" : c.type === "date" ? "date" : "text";
        input = `<input type="${t}" id="${id}" value="${esc(val ?? "")}">`;
    }
    return `<div class="form-group"><label>${esc(c.label)}${c.req ? " *" : ""}</label>${input}</div>`;
}

async function preencherSelect(sel, de, placeholder) {
    try {
        const itens = await api.get(de.endpoint);
        sel.innerHTML = `<option value="">${esc(placeholder)}</option>` +
            itens.map((it) => `<option value="${esc(it[de.val])}">${esc(it[de.txt])}</option>`).join("");
    } catch (_) {
        sel.innerHTML = `<option value="">${esc(placeholder)}</option>`;
    }
}

function fecharModal() {
    document.getElementById("modal").classList.remove("open");
}

async function salvarModal(ev) {
    ev.preventDefault();
    const form = document.getElementById("modal-form");
    const k = form.dataset.ent;
    const id = form.dataset.id;
    const e = ENT[k];
    const editando = !!id;
    const campos = e.campos.filter((c) => !(editando && c.novo));

    const dados = {};
    for (const c of campos) {
        const el = document.getElementById("f-" + c.k);
        let val;
        if (c.type === "checkbox") val = el.checked;
        else if (c.type === "csv") val = el.value.split(",").map((s) => s.trim()).filter(Boolean);
        else if (c.type === "number") val = el.value === "" ? null : Number(el.value);
        else val = el.value.trim();

        if (c.req && (val === "" || val === null)) {
            toast(`Preencha o campo: ${c.label}`, "error");
            el.focus();
            return;
        }
        dados[c.k] = val;
    }

    try {
        const url = editando ? `${e.endpoint}/${id}` : e.endpoint;
        const res = editando ? await api.put(url, dados) : await api.post(url, dados);
        if (res && res.erro) return toast(res.erro, "error");
        toast(editando ? "Atualizado com sucesso." : "Cadastrado com sucesso.", "success");
        fecharModal();
        loadPanel(k);
    } catch (_) {
        toast("Falha ao salvar.", "error");
    }
}

// ============================================================
// Utils
// ============================================================
function badges(arr) {
    if (!arr || !arr.length) return `<span class="badge badge-muted">nenhuma</span>`;
    return arr.map((a) => `<span class="badge">${esc(a)}</span>`).join(" ");
}

// ---- Atendimentos (3.1 / 3.2 / 3.3 / 3.5) ----
async function loadAtendimentos() {
    const tbody = document.getElementById("tabela-atendimentos-full");
    try {
        atendimentosCache = await api.get("/atendimentos");
        if (!atendimentosCache.length) {
            tbody.innerHTML = `<tr><td colspan="6" class="empty">Nenhum atendimento.</td></tr>`;
            return;
        }
        tbody.innerHTML = atendimentosCache
            .map((a) => `<tr>
                <td>${esc(a.data_hora)}</td>
                <td>${esc(a.paciente)}</td>
                <td>${esc(a.residente)}</td>
                <td>${esc(a.preceptor)}</td>
                <td>${a.duracao_minutos}</td>
                <td><button class="btn btn-primary btn-sm" data-id="${a.id_atendimento}">Procedimentos</button></td>
            </tr>`)
            .join("");
        tbody.querySelectorAll("[data-id]").forEach((btn) =>
            btn.addEventListener("click", () => abrirModalProcedimentos(Number(btn.dataset.id)))
        );
    } catch (_) {
        tbody.innerHTML = `<tr><td colspan="6" class="empty">Erro ao carregar (a API está no ar?).</td></tr>`;
    }
}

function setupAtendimentoModal() {
    document.getElementById("btn-novo-atendimento").addEventListener("click", abrirModalNovoAtendimento);
    document.getElementById("btn-cancelar-atendimento").addEventListener("click", () =>
        document.getElementById("modal-atendimento").classList.remove("open")
    );
    document.getElementById("modal-atendimento").addEventListener("click", (e) => {
        if (e.target.id === "modal-atendimento") e.currentTarget.classList.remove("open");
    });
    document.getElementById("form-atendimento").addEventListener("submit", salvarAtendimento);
}

async function abrirModalNovoAtendimento() {
    document.getElementById("form-atendimento").reset();
    try {
        const [pacs, ress, precs] = await Promise.all([
            api.get("/pacientes-lookup"),
            api.get("/residentes"),
            api.get("/preceptores"),
        ]);
        preencherSelectSimples("atd-paciente", pacs, "id");
        preencherSelectSimples("atd-residente", ress, "id_pessoa");
        preencherSelectSimples("atd-preceptor", precs, "id_pessoa");
        document.getElementById("modal-atendimento").classList.add("open");
    } catch (_) {
        toast("Erro ao carregar dados do formulário.", "error");
    }
}

async function salvarAtendimento(e) {
    e.preventDefault();
    const body = {
        data_hora: document.getElementById("atd-data-hora").value,
        duracao_minutos: document.getElementById("atd-duracao").value,
        id_paciente: document.getElementById("atd-paciente").value,
        id_residente: document.getElementById("atd-residente").value,
        id_preceptor: document.getElementById("atd-preceptor").value,
    };
    try {
        const res = await api.post("/atendimentos", body);
        if (res.erro) return toast(res.erro, "error");
        toast("Atendimento criado.", "success");
        document.getElementById("modal-atendimento").classList.remove("open");
        loadAtendimentos();
    } catch (_) {
        toast("Falha ao salvar.", "error");
    }
}

// ---- Procedimentos do atendimento (3.3 / 3.5) ----
function setupProcedimentosModal() {
    document.getElementById("btn-fechar-procedimentos").addEventListener("click", () =>
        document.getElementById("modal-procedimentos").classList.remove("open")
    );
    document.getElementById("modal-procedimentos").addEventListener("click", (e) => {
        if (e.target.id === "modal-procedimentos") e.currentTarget.classList.remove("open");
    });
    document.getElementById("form-procedimento-realizado").addEventListener("submit", adicionarProcedimento);
}

async function abrirModalProcedimentos(id_atendimento) {
    atendimentoAtual = id_atendimento;
    document.getElementById("proc-atd-id").textContent = `#${id_atendimento}`;
    document.getElementById("form-procedimento-realizado").reset();
    try {
        const catalogo = await api.get("/procedimentos");
        preencherSelectSimples("proc-catalog", catalogo, "id", (p) => `${p.codigo} — ${p.nome}`);
    } catch (_) { /* segue mesmo se catálogo falhar */ }
    document.getElementById("modal-procedimentos").classList.add("open");
    renderProcedimentosDoAtendimento();
}

async function renderProcedimentosDoAtendimento() {
    const tbody = document.getElementById("tabela-procedimentos-atd");
    try {
        const dados = await api.get(`/atendimentos/${atendimentoAtual}/procedimentos`);
        if (!dados.length) {
            tbody.innerHTML = `<tr><td colspan="6" class="empty">Nenhum procedimento realizado.</td></tr>`;
            return;
        }
        tbody.innerHTML = dados.map((d) => {
            const riscoClass = d.nivel_risco === "ALTO" ? "badge-danger"
                             : d.nivel_risco === "MEDIO" ? "badge-warn" : "";
            const status = d.faturado
                ? `<span class="badge badge-muted">faturado</span>`
                : `<span class="badge">pendente</span>`;
            const btn = d.faturado
                ? ``
                : `<button class="btn btn-danger btn-sm" data-proc="${d.id_procedimento}">Remover</button>`;
            return `<tr>
                <td>${esc(d.procedimento)}</td>
                <td><span class="badge ${riscoClass}">${esc(d.nivel_risco)}</span></td>
                <td>${d.quantidade}</td>
                <td>${d.tempo_real_minutos} min</td>
                <td>${status}</td>
                <td>${btn}</td>
            </tr>`;
        }).join("");
        tbody.querySelectorAll("[data-proc]").forEach((b) =>
            b.addEventListener("click", () => removerProcedimento(Number(b.dataset.proc)))
        );
    } catch (_) {
        tbody.innerHTML = `<tr><td colspan="6" class="empty">Erro ao carregar.</td></tr>`;
    }
}

async function adicionarProcedimento(e) {
    e.preventDefault();
    const body = {
        id_procedimento: document.getElementById("proc-catalog").value,
        quantidade: document.getElementById("proc-qtd").value,
        tempo_real_minutos: document.getElementById("proc-tempo").value,
        observacao: document.getElementById("proc-obs").value.trim() || null,
    };
    try {
        const res = await api.post(`/atendimentos/${atendimentoAtual}/procedimentos`, body);
        if (res.erro) return toast(res.erro, "error");
        toast("Procedimento adicionado.", "success");
        document.getElementById("form-procedimento-realizado").reset();
        document.getElementById("proc-qtd").value = 1;
        renderProcedimentosDoAtendimento();
    } catch (_) {
        toast("Falha ao adicionar.", "error");
    }
}

async function removerProcedimento(id_procedimento) {
    try {
        const res = await fetch(`/api/atendimentos/${atendimentoAtual}/procedimentos/${id_procedimento}`, { method: "DELETE" });
        const data = await res.json();
        if (!res.ok) return toast(data.erro || "Erro ao remover.", "error");
        toast("Procedimento removido.", "success");
        renderProcedimentosDoAtendimento();
    } catch (_) {
        toast("Falha ao remover.", "error");
    }
}

function preencherSelectSimples(id, itens, valKey, txtFn) {
    const sel = document.getElementById(id);
    sel.innerHTML = itens
        .map((i) => `<option value="${esc(i[valKey])}">${esc(txtFn ? txtFn(i) : i.nome)}</option>`)
        .join("");
}

// ---- utils ----
function toast(msg, type = "") {
    const el = document.getElementById("toast");
    el.textContent = msg;
    el.className = `toast show ${type}`;
    clearTimeout(el._t);
    el._t = setTimeout(() => (el.className = "toast"), 3200);
}

function esc(v) {
    return String(v ?? "").replace(/[&<>"']/g, (c) =>
        ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
    );
}
