/* Camada única de acesso à API do backend + controle de sessão no navegador. */

const API_BASE = `${window.location.origin}/api`;
const CHAVE_TOKEN = "viajai:token";
const CHAVE_USUARIO = "viajai:usuario";

const Sessao = {
  salvar(token, usuario) {
    localStorage.setItem(CHAVE_TOKEN, token);
    localStorage.setItem(CHAVE_USUARIO, JSON.stringify(usuario || {}));
  },
  atualizarUsuario(usuario) {
    localStorage.setItem(CHAVE_USUARIO, JSON.stringify(usuario || {}));
  },
  token() {
    return localStorage.getItem(CHAVE_TOKEN);
  },
  usuario() {
    try {
      return JSON.parse(localStorage.getItem(CHAVE_USUARIO) || "null");
    } catch {
      return null;
    }
  },
  limpar() {
    localStorage.removeItem(CHAVE_TOKEN);
    localStorage.removeItem(CHAVE_USUARIO);
  },
  exigirLogin() {
    if (!this.token()) {
      window.location.href = "login.html";
      return false;
    }
    return true;
  },
};

class ErroApi extends Error {
  constructor(mensagem, status, campo) {
    super(mensagem);
    this.status = status;
    this.campo = campo;
  }
}

async function requisitar(caminho, { metodo = "GET", corpo = null, autenticado = true } = {}) {
  const cabecalhos = { "Content-Type": "application/json" };
  const token = Sessao.token();
  if (autenticado && token) cabecalhos.Authorization = `Bearer ${token}`;

  let resposta;
  try {
    resposta = await fetch(`${API_BASE}${caminho}`, {
      method: metodo,
      headers: cabecalhos,
      body: corpo ? JSON.stringify(corpo) : undefined,
    });
  } catch {
    throw new ErroApi("Não foi possível falar com o servidor. Ele está rodando?", 0);
  }

  const texto = await resposta.text();
  const dados = texto ? JSON.parse(texto) : {};

  if (!resposta.ok) {
    if (resposta.status === 401 && autenticado) {
      Sessao.limpar();
      if (!window.location.pathname.endsWith("login.html")) window.location.href = "login.html";
    }
    throw new ErroApi(dados.erro || "Algo deu errado.", resposta.status, dados.campo);
  }
  return dados;
}

const Api = {
  // autenticação
  cadastrar: (dados) => requisitar("/auth/cadastro", { metodo: "POST", corpo: dados, autenticado: false }),
  verificarCodigo: (dados) => requisitar("/auth/verificar", { metodo: "POST", corpo: dados, autenticado: false }),
  reenviarCodigo: (email) => requisitar("/auth/reenviar-codigo", { metodo: "POST", corpo: { email }, autenticado: false }),
  entrar: (dados) => requisitar("/auth/login", { metodo: "POST", corpo: dados, autenticado: false }),
  sair: () => requisitar("/auth/logout", { metodo: "POST" }),

  // usuário e preferências
  perfil: () => requisitar("/usuarios/eu"),
  opcoesPreferencias: () => requisitar("/preferencias/opcoes", { autenticado: false }),
  salvarPreferencias: (dados) => requisitar("/preferencias", { metodo: "PUT", corpo: dados }),

  // lugares
  listarLugares: (categoria) => requisitar(`/lugares${categoria && categoria !== "todos" ? `?categoria=${categoria}` : ""}`),
  buscarLugares: (filtros) => requisitar(`/lugares/busca?${new URLSearchParams(filtros)}`),
  recomendacoes: (limite = 8, categoria) =>
    requisitar(`/lugares/recomendacoes?limite=${limite}${categoria && categoria !== "todos" ? `&categoria=${categoria}` : ""}`),
  detalharLugar: (id) => requisitar(`/lugares/${id}`),

  // favoritos
  listarFavoritos: () => requisitar("/favoritos"),
  salvarFavorito: (lugarId) => requisitar("/favoritos", { metodo: "POST", corpo: { lugar_id: lugarId } }),
  removerFavorito: (lugarId) => requisitar(`/favoritos/${lugarId}`, { metodo: "DELETE" }),

  // chat com IA
  historicoChat: () => requisitar("/chat"),
  enviarMensagem: (texto) => requisitar("/chat", { metodo: "POST", corpo: { texto } }),
};

/* Utilidades de interface -------------------------------------------------- */
function mostrarAlerta(elemento, mensagem, tipo = "erro") {
  if (!elemento) return;
  elemento.textContent = mensagem;
  elemento.className = `alerta alerta--${tipo} visivel`;
}

function esconderAlerta(elemento) {
  if (elemento) elemento.className = "alerta";
}

function urlImagem(nomeArquivo) {
  return `assets/${nomeArquivo || "card-praia.svg"}`;
}
