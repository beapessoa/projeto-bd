// Roteamento simples + carregamento das telas.
const LOADERS = { dashboard: loadDashboard, pacientes: loadPacientes };
let pacientesCache = [];

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
    renderTabela("/atendimentos-recentes", "tabela-atendimentos", 5, (a) =>
        `<td>${esc(a.data_hora)}</td><td>${esc(a.paciente)}</td><td>${esc(a.residente)}</td>` +
        `<td>${esc(a.preceptor)}</td><td>${a.duracao_minutos}</td>`
    );
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
