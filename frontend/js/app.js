// Roteamento simples + carregamento das telas.
const LOADERS = {
    dashboard: loadDashboard,
    pacientes: loadPacientes,
    atendimentos: loadAtendimentos,
};
let pacientesCache = [];
let atendimentosCache = [];
let atendimentoAtual = null;

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

    setupModal();
    setupAtendimentoModal();
    setupProcedimentosModal();
    setupFiltroPreceptores();
    showPage("dashboard");
});

function showPage(page) {
    document.querySelectorAll(".page").forEach((s) => (s.hidden = true));
    document.getElementById(`page-${page}`).hidden = false;
    (LOADERS[page] || (() => {}))();
}

// ---- Dashboard ----
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

// ---- Pacientes ----
async function loadPacientes() {
    const tbody = document.getElementById("tabela-pacientes");
    try {
        pacientesCache = await api.get("/pacientes");
        if (!pacientesCache.length) {
            tbody.innerHTML = `<tr><td colspan="7" class="empty">Nenhum paciente.</td></tr>`;
            return;
        }
        tbody.innerHTML = pacientesCache
            .map((p) => {
                const alergias = p.alergias && p.alergias.length
                    ? p.alergias.map((a) => `<span class="badge">${esc(a)}</span>`).join(" ")
                    : `<span class="badge badge-muted">nenhuma</span>`;
                return `<tr>
                    <td>${esc(p.nome)}</td>
                    <td>${esc(p.cpf)}</td>
                    <td>${esc(p.num_convenio || "—")}</td>
                    <td>${esc(p.grupo_sanguineo)}</td>
                    <td>${esc(p.endereco || "—")}</td>
                    <td>${alergias}</td>
                    <td><button class="btn btn-primary btn-sm" data-id="${p.id_pessoa}">Editar</button></td>
                </tr>`;
            })
            .join("");
        tbody.querySelectorAll("[data-id]").forEach((btn) =>
            btn.addEventListener("click", () =>
                abrirModal(pacientesCache.find((p) => p.id_pessoa === Number(btn.dataset.id)))
            )
        );
    } catch (_) {
        tbody.innerHTML = `<tr><td colspan="7" class="empty">Erro ao carregar (a API está no ar?).</td></tr>`;
    }
}

// ---- Modal editar paciente (3.4) ----
function setupModal() {
    document.getElementById("btn-cancelar").addEventListener("click", fecharModal);
    document.getElementById("modal-paciente").addEventListener("click", (e) => {
        if (e.target.id === "modal-paciente") fecharModal();
    });
    document.getElementById("form-paciente").addEventListener("submit", salvarPaciente);
}

function abrirModal(p) {
    document.getElementById("pac-id").value = p.id_pessoa;
    document.getElementById("pac-convenio").value = p.num_convenio || "";
    document.getElementById("pac-grupo").value = p.grupo_sanguineo;
    document.getElementById("pac-endereco").value = p.endereco || "";
    document.getElementById("pac-alergias").value = (p.alergias || []).join(", ");
    document.getElementById("modal-paciente").classList.add("open");
}

function fecharModal() {
    document.getElementById("modal-paciente").classList.remove("open");
}

async function salvarPaciente(e) {
    e.preventDefault();
    const id = document.getElementById("pac-id").value;
    const body = {
        num_convenio: document.getElementById("pac-convenio").value.trim() || null,
        grupo_sanguineo: document.getElementById("pac-grupo").value,
        endereco: document.getElementById("pac-endereco").value.trim() || null,
        alergias: document.getElementById("pac-alergias").value
            .split(",").map((s) => s.trim()).filter(Boolean),
    };
    try {
        const res = await api.put(`/pacientes/${id}`, body);
        if (res.erro) return toast(res.erro, "error");
        toast("Paciente atualizado com sucesso.", "success");
        fecharModal();
        loadPacientes();
    } catch (_) {
        toast("Falha ao salvar.", "error");
    }
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
        preencherSelect("atd-paciente", pacs);
        preencherSelect("atd-residente", ress);
        preencherSelect("atd-preceptor", precs);
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
        preencherSelect("proc-catalog", catalogo, (p) => `${p.codigo} — ${p.nome}`);
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

function preencherSelect(id, itens, labelFn) {
    const sel = document.getElementById(id);
    sel.innerHTML = itens
        .map((i) => `<option value="${i.id}">${esc(labelFn ? labelFn(i) : i.nome)}</option>`)
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
