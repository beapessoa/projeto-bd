// ============================================================
// Constantes
// ============================================================
const GRUPOS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"];
const DIAS = ["Segunda", "Terca", "Quarta", "Quinta", "Sexta", "Sabado", "Domingo"];
const TURNOS = ["Manha", "Tarde", "Noite"];
const TIPOS_UNIDADE = ["Enfermaria", "UTI", "Pronto-Socorro", "Ambulatorio"];
const ANOS_RES = ["R1", "R2", "R3"];
const TITULACOES = ["Especialista", "Mestre", "Doutor", "Pos-Doutor", "Livre-Docente"];
let atendimentosCache = [];
let atendimentoAtual = null;

const AVATAR_COLORS = [
    { bg: "#eaf3ff", color: "#2f6bd6" },
    { bg: "#eef1f7", color: "#4a5a78" },
    { bg: "#e6f6f2", color: "#12907e" },
    { bg: "#f0edfc", color: "#6b4fd0" },
    { bg: "#e9f0ff", color: "#3b6fb8" },
];

const BAR_COLORS = ["#13233f", "#2f6bd6", "#4a90ff", "#6fa8ff", "#a9cbff"];

const PAGE_META = {
    dashboard:     { breadcrumb: "Visão geral",   title: "Dashboard",     desc: "Acompanhe atendimentos, residentes e tempos médios do hospital em um só lugar." },
    pacientes:     { breadcrumb: "Registros",      title: "Pacientes",     desc: "Gerencie os pacientes cadastrados, convênios, grupos sanguíneos e alergias." },
    profissionais: { breadcrumb: "Equipe",         title: "Profissionais", desc: "Gerencie residentes e preceptores do hospital." },
    unidades:      { breadcrumb: "Infraestrutura", title: "Unidades",      desc: "Gerencie as unidades hospitalares e seus leitos." },
    escalas:       { breadcrumb: "Planejamento",   title: "Escalas",       desc: "Visualize e gerencie as escalas de plantão." },
    atendimentos:  { breadcrumb: "Registros",      title: "Atendimentos",  desc: "Registre e acompanhe os atendimentos realizados." },
};

// ============================================================
// Configuração de cada entidade
// ============================================================
const ENT = {
    pacientes: {
        titulo: "Pacientes", singular: "Paciente", endpoint: "/pacientes", id: "id_pessoa",
        colunas: [
            ["Nome", (r) => `<div class="cell-with-avatar">${avatarHtml(r.nome, true)}${esc(r.nome)}</div>`],
            ["CPF", (r) => esc(r.cpf)],
            ["Convênio", (r) => esc(r.num_convenio || "—")],
            ["Grupo", (r) => `<span class="badge badge-blood">${esc(r.grupo_sanguineo)}</span>`],
            ["Endereço", (r) => esc(r.endereco || "—")],
            ["Alergias", (r) => badges(r.alergias)],
            ["Atendimentos", (r) => `<button class="btn btn-outline btn-sm" data-atd-pac="${r.id_pessoa}" data-atd-nome="${esc(r.nome)}">Ver</button>`],
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
            ["Nome", (r) => `<div class="cell-with-avatar">${avatarHtml(r.nome, true)}${esc(r.nome)}</div>`],
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
            ["Nome", (r) => `<div class="cell-with-avatar">${avatarHtml(r.nome, true)}${esc(r.nome)}</div>`],
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
    const navTabs = document.querySelectorAll(".nav-tab");

    navTabs.forEach((tab) => {
        tab.addEventListener("click", (e) => {
            e.preventDefault();
            navTabs.forEach((t) => t.classList.remove("active"));
            tab.classList.add("active");
            showPage(tab.dataset.page);
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

    document.getElementById("btn-fechar-atd-pac").addEventListener("click", () =>
        document.getElementById("modal-atendimentos-paciente").classList.remove("open")
    );
    document.getElementById("modal-atendimentos-paciente").addEventListener("click", (e) => {
        if (e.target.id === "modal-atendimentos-paciente") e.currentTarget.classList.remove("open");
    });

    showPage("dashboard");
});

function showPage(page) {
    document.querySelectorAll(".page").forEach((s) => (s.hidden = true));

    const meta = PAGE_META[page];
    if (meta) {
        document.getElementById("page-breadcrumb").textContent = meta.breadcrumb;
        document.getElementById("page-title").textContent = meta.title;
        document.getElementById("page-desc").textContent = meta.desc;
    }

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

    renderTempoMedio();

    let pos = 0;
    renderTabela("/analiticas/ranking-residentes", "tabela-ranking-residentes", 3, (d) =>
        `<td>${++pos}º</td><td><div class="cell-with-avatar">${avatarHtml(d.residente, true)}${esc(d.residente)}</div></td><td>${d.total_atendimentos}</td>`
    );

    renderTabela("/analiticas/plantoes-por-residente", "tabela-plantoes", 3, (d) =>
        `<td>${esc(d.unidade)}</td><td>${esc(d.residente)}</td><td>${d.qtd_plantoes}</td>`
    );

    renderTabela("/analiticas/pacientes-sem-risco-alto", "tabela-sem-risco-alto", 4, (p) =>
        `<td>${esc(p.nome)}</td><td>${esc(p.cpf)}</td><td>${esc(p.num_convenio || "—")}</td>` +
        `<td><span class="badge badge-blood">${esc(p.grupo_sanguineo)}</span></td>`
    );

    renderTabela("/atendimentos-recentes", "tabela-atendimentos", 5, (a) =>
        `<td>${esc(a.data_hora)}</td><td>${esc(a.paciente)}</td><td>${esc(a.residente)}</td>` +
        `<td>${esc(a.preceptor)}</td><td>${a.duracao_minutos}</td>`
    );
}

async function renderTempoMedio() {
    const container = document.getElementById("tempo-medio-bars");
    try {
        const dados = await api.get("/tempo-medio-residente");
        if (!dados.length) {
            container.innerHTML = '<p class="empty-text">Sem dados.</p>';
            return;
        }
        const max = Math.max(...dados.map((d) => d.tempo_medio_minutos));
        container.innerHTML = dados
            .map((d, i) => {
                const pct = max > 0 ? (d.tempo_medio_minutos / max) * 100 : 0;
                const barColor = BAR_COLORS[i % BAR_COLORS.length];
                return `<div class="bar-row">
                    ${avatarHtml(d.residente, true)}
                    <div class="bar-info">
                        <span class="bar-name">${esc(d.residente)}</span>
                        <span class="bar-meta">${d.qtd_atendimentos} atend.</span>
                    </div>
                    <div class="bar-track"><div class="bar-fill" style="width:${pct}%;background:${barColor}"></div></div>
                    <span class="bar-value">${d.tempo_medio_minutos} min</span>
                </div>`;
            })
            .join("");
    } catch (_) {
        container.innerHTML = '<p class="empty-text">Erro ao carregar.</p>';
    }
}

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
// Painéis de cadastro
// ============================================================
function panelHtml(k) {
    const e = ENT[k];
    const ths = e.colunas.map((c) => `<th>${c[0]}</th>`).join("") + (e.semEdicao ? "" : "<th></th>");
    const nCols = e.colunas.length + (e.semEdicao ? 0 : 1);
    const filtros = e.filtros
        ? `<div class="filtros" data-filtros="${k}">${e.filtros.map((f) =>
              `<select data-filtro="${f.k}" class="filter-select"><option value="">${esc(f.label)}: todos</option>` +
              (f.opcoes || []).map((o) => `<option value="${esc(o)}">${esc(o)}</option>`).join("") +
              `</select>`).join("")}</div>`
        : "";
    return `<div class="section-card" style="margin-bottom:20px;">
        <div class="section-card-header">
            <div class="section-card-title-group">
                <h3 class="section-card-title">${e.titulo}</h3>
                <span class="count-badge" data-count="${k}"></span>
            </div>
            <button class="btn btn-accent btn-sm" data-novo="${k}">+ Novo ${e.singular.toLowerCase()}</button>
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
        const countEl = document.querySelector(`[data-count="${k}"]`);
        if (countEl) countEl.textContent = `${dados.length} cadastrados`;

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
        tbody.querySelectorAll("[data-atd-pac]").forEach((btn) =>
            btn.addEventListener("click", () =>
                abrirModalAtendimentosPaciente(Number(btn.dataset.atdPac), btn.dataset.atdNome)
            )
        );
    } catch (_) {
        tbody.innerHTML = `<tr><td colspan="${nCols}" class="empty">Erro ao carregar (a API está no ar?).</td></tr>`;
    }
}

function linhaHtml(k, r) {
    const e = ENT[k];
    const tds = e.colunas.map((c) => `<td>${c[1](r)}</td>`).join("");
    const acao = e.semEdicao
        ? ""
        : `<td><button class="btn-edit" data-editar data-id="${esc(r[e.id])}">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/></svg>
            Editar
          </button></td>`;
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
// Atendimentos
// ============================================================
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
                <td><button class="btn btn-dark btn-sm" data-id="${a.id_atendimento}">Procedimentos</button></td>
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

// ============================================================
// Atendimentos de um paciente (3.2)
// ============================================================
async function abrirModalAtendimentosPaciente(id_pessoa, nome) {
    document.getElementById("atd-pac-nome").textContent = nome || "";
    document.getElementById("modal-atendimentos-paciente").classList.add("open");
    const tbody = document.getElementById("tabela-atendimentos-paciente");
    tbody.innerHTML = `<tr><td colspan="4" class="empty">Carregando...</td></tr>`;
    try {
        const dados = await api.get(`/pacientes/${id_pessoa}/atendimentos`);
        tbody.innerHTML = dados.length
            ? dados.map((a) => `<tr>
                <td>${esc(a.data_hora)}</td>
                <td>${a.duracao_minutos}</td>
                <td>${esc(a.residente)}</td>
                <td>${esc(a.preceptor)}</td>
            </tr>`).join("")
            : `<tr><td colspan="4" class="empty">Este paciente ainda não tem atendimentos.</td></tr>`;
    } catch (_) {
        tbody.innerHTML = `<tr><td colspan="4" class="empty">Erro ao carregar.</td></tr>`;
    }
}

// ============================================================
// Procedimentos do atendimento
// ============================================================
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

// ============================================================
// Utilitários
// ============================================================
function getInitials(name) {
    const parts = (name || "").trim().split(/\s+/);
    if (parts.length <= 1) return (parts[0] || "?").charAt(0).toUpperCase();
    return (parts[0].charAt(0) + parts[parts.length - 1].charAt(0)).toUpperCase();
}

function avatarHtml(name, sm) {
    const initials = getInitials(name);
    let hash = 0;
    for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
    const c = AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
    const cls = sm ? "avatar avatar-sm" : "avatar";
    return `<span class="${cls}" style="background:${c.bg};color:${c.color}">${esc(initials)}</span>`;
}

function badges(arr) {
    if (!arr || !arr.length) return `<span class="badge badge-muted">nenhuma</span>`;
    return arr.map((a) => `<span class="badge badge-allergy">${esc(a)}</span>`).join(" ");
}

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
