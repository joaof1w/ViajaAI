/* Conversa com o assistente de IA (Vai). */

if (Sessao.exigirLogin()) {
  const listaMensagens = document.getElementById("mensagens");
  const entrada = document.getElementById("entrada");
  const botaoEnviar = document.getElementById("botao-enviar");
  const areaSugestoes = document.getElementById("sugestoes");

  carregarHistorico();

  async function carregarHistorico() {
    try {
      const dados = await Api.historicoChat();
      dados.mensagens.forEach((mensagem) => adicionarMensagem(mensagem.autor, mensagem.texto));
      montarSugestoes(dados.sugestoes);
    } catch (erro) {
      adicionarMensagem("ia", `Não consegui carregar a conversa: ${erro.message}`);
    }
  }

  function montarSugestoes(sugestoes) {
    areaSugestoes.innerHTML = "";
    (sugestoes || []).forEach((texto) => {
      const botao = document.createElement("button");
      botao.className = "sugestao";
      botao.type = "button";
      botao.textContent = texto;
      botao.addEventListener("click", () => enviar(texto));
      areaSugestoes.appendChild(botao);
    });
  }

  function adicionarMensagem(autor, texto) {
    const bloco = document.createElement("div");
    bloco.className = `mensagem mensagem--${autor === "ia" ? "ia" : "usuario"}`;
    const mini = document.createElement("div");
    mini.className = "mensagem__mini";
    mini.textContent = autor === "ia" ? "🧳" : (Sessao.usuario()?.iniciais || "EU");
    const bolha = document.createElement("div");
    bolha.className = "mensagem__bolha";
    bolha.textContent = texto;
    bloco.append(mini, bolha);
    listaMensagens.appendChild(bloco);
    listaMensagens.scrollTop = listaMensagens.scrollHeight;
    return bloco;
  }

  function mostrarDigitando() {
    const bloco = document.createElement("div");
    bloco.className = "mensagem mensagem--ia";
    bloco.id = "digitando";
    bloco.innerHTML = `
      <div class="mensagem__mini">🧳</div>
      <div class="mensagem__bolha digitando"><span></span><span></span><span></span></div>`;
    listaMensagens.appendChild(bloco);
    listaMensagens.scrollTop = listaMensagens.scrollHeight;
  }

  async function enviar(texto) {
    const pergunta = (texto || entrada.value).trim();
    if (!pergunta) return;

    entrada.value = "";
    adicionarMensagem("usuario", pergunta);
    mostrarDigitando();
    botaoEnviar.disabled = true;

    try {
      const resposta = await Api.enviarMensagem(pergunta);
      document.getElementById("digitando")?.remove();
      adicionarMensagem("ia", resposta.resposta.texto);
      document.getElementById("selo-ia").textContent = resposta.origem === "gemini" ? "Gemini" : "IA";
    } catch (erro) {
      document.getElementById("digitando")?.remove();
      adicionarMensagem("ia", `Ops: ${erro.message}`);
    } finally {
      botaoEnviar.disabled = false;
      entrada.focus();
    }
  }

  document.getElementById("form-chat").addEventListener("submit", (evento) => {
    evento.preventDefault();
    enviar();
  });
}
