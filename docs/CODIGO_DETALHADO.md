# Viajaí — código detalhado, arquivo por arquivo

Cada capítulo explica **um arquivo**: o que faz e por quê (texto escrito à mão) e, logo abaixo, a **estrutura real extraída do código** — classes, métodos, funções, rotas, colunas das tabelas, quem usa quem e quais endpoints cada tela chama. Como a estrutura é gerada automaticamente a partir do código, ela não envelhece sozinha.

**Como ler:** os caminhos de `backend/` aparecem sem o prefixo nas listas de dependência (ex.: `services/viagens_service.py`). 🔒 = exige login. "Usa" = arquivos do projeto que este importa; "Usado por" = quem o importa.


---

## 1. Raiz do projeto

### `.env.example`  <small>(44 linhas)</small>

Modelo do arquivo `.env`. Documenta cada variável: chave secreta, banco, Gemini, e-mail/SMTP, regras de senha, e na expansão as integrações externas (User-Agent, Pexels, Unsplash, mapa) e os limites de upload. O `.env` real nunca vai para o Git.

### `.gitignore`  <small>(13 linhas)</small>

Arquivos que o Git ignora: `.env` (segredos), `*.db` (banco local), `backend/uploads/` (fotos de usuários), caches Python e a trava de inicialização `.inicializacao.lock`.

### `DEPLOY.md`  <small>(70 linhas)</small>

Guia de publicação gratuita (PythonAnywhere e Render), com as variáveis obrigatórias em produção e as duas formas de entregar o código de verificação do cadastro.

### `Procfile`  <small>(2 linhas)</small>

Uma linha que diz a plataformas como Render/Heroku qual comando inicia o site: `gunicorn wsgi:app` com 2 processos e 4 threads cada.

### `README.md`  <small>(322 linhas)</small>

Documentação geral do projeto: funcionalidades, como executar, variáveis de ambiente, tabelas, endpoints, segurança e testes.

### `render.yaml`  <small>(21 linhas)</small>

Receita (*blueprint*) do Render no plano gratuito: instala dependências, inicia o gunicorn, define `FLASK_DEBUG=0` e gera uma `SECRET_KEY` aleatória. O aviso no topo lembra que o disco gratuito é apagado a cada reinício (o SQLite e as fotos somem).

### `requirements.txt`  <small>(15 linhas)</small>

Lista das bibliotecas Python: Flask (servidor), Flask-SQLAlchemy/SQLAlchemy (banco), Flask-Cors, python-dotenv (lê o `.env`), requests (chamadas externas), **Pillow** (trata as fotos enviadas) e **gunicorn** (servidor de produção, não instalado no Windows).

### `run.py`  <small>(10 linhas)</small>

Ponto de entrada para **desenvolvimento**. Cria o app com `create_app()` e o executa com o servidor embutido do Flask (porta e modo debug vêm do `Config`). Em produção não se usa: veja `wsgi.py`.

**Usa:** `app.py`, `config.py`  
**Usado por:** —

### `wsgi.py`  <small>(8 linhas)</small>

Ponto de entrada para **produção**. Apenas cria o objeto `app` no nível do módulo, que é o formato que gunicorn, PythonAnywhere e similares esperam (`gunicorn wsgi:app`).

**Usa:** `app.py`  
**Usado por:** —

---

## 2. Backend — núcleo

### `backend/__init__.py`  <small>(1 linhas)</small>

Arquivo vazio que faz da pasta `backend` um pacote Python (permite `from backend.app import ...`).

### `backend/app.py`  <small>(163 linhas)</small>

Fábrica da aplicação Flask (`create_app`). Na ordem: carrega o `Config`; **recusa subir em produção com a SECRET_KEY padrão**; inicializa banco e CORS; registra Controllers, tratadores de erro (sempre respondem JSON), cabeçalhos de segurança e as rotas do frontend; dentro de um **bloqueio entre processos** cria as tabelas, roda as migrações e a carga inicial; por fim dispara a sincronização de fotos em segundo plano (só em desenvolvimento/produção, nunca em teste).
Detalhes importantes: o *listener* `_ativar_chaves_estrangeiras` liga `PRAGMA foreign_keys=ON` no SQLite (sem isso as regras `ON DELETE` não valem); o bloqueio (`fcntl`) evita que vários workers do gunicorn criem tabelas/dados ao mesmo tempo; a CSP só libera scripts da própria origem e imagens de Wikimedia, Pexels, Unsplash e tiles do OpenStreetMap.

**Estrutura**

- **Constantes:** `PASTA_FRONTEND`
- **Função `create_app(config)`**
- **Função `_bloqueio_de_inicializacao()`** — Exclusão mútua entre processos na mesma máquina (fcntl; sem efeito no Windows).
- **Função `_ativar_chaves_estrangeiras(conexao, _registro)`** — SQLite só respeita integridade referencial (ON DELETE...) com esta pragma.
- **Função `iniciar_sincronizacao_de_fotos(app)`** — Busca fotos reais (Wikimedia) em segundo plano para lugares ainda sem foto.
- **Função `registrar_controllers(app)`** — Cada Controller é uma classe responsável por um recurso do sistema.
- **Função `registrar_tratadores_de_erro(app)`**
- **Função `registrar_cabecalhos_de_seguranca(app)`**
- **Função `registrar_frontend(app)`** — Serve o frontend estático na mesma origem da API.

**Usa:** `config.py`, `extensions.py`, `migracoes.py`, `seeds.py`, `services/fotos_lugar_service.py`, `utils/erros.py`  
**Usado por:** `tests/apoio.py`, `tests/test_funcionalidades.py`, `run.py`, `tools/fotos.py`, `wsgi.py`

### `backend/config.py`  <small>(83 linhas)</small>

Classe `Config` com todas as configurações lidas de variáveis de ambiente (com valores padrão seguros para desenvolvimento). Agrupa: Flask, banco, Gemini, e-mail, regras de negócio, **uploads** (pasta, tamanho, quantidade, lado máximo, validade da URL assinada) e **integrações externas** (liga/desliga, User-Agent, endpoints, chaves de Pexels/Unsplash, tiles do mapa). `MAX_CONTENT_LENGTH` limita o corpo de qualquer requisição.

**Estrutura**

- **Constantes:** `BASE_DIR`
- **Classe `Config`**

**Usa:** —  
**Usado por:** `app.py`, `models/codigo_verificacao.py`, `repositories/relatorio_repository.py`, `services/avaliacoes_service.py`, `services/cadastrar_usuario_service.py`, `services/diario_service.py`, `services/envio_email_service.py`, `services/fotos_lugar_service.py`, `services/gemini_service.py`, `services/integracoes/cliente_http.py`, `services/integracoes/clima_service.py`, `services/integracoes/fotos_pexels_service.py` e mais 11

### `backend/extensions.py`  <small>(7 linhas)</small>

Cria uma única vez os objetos `db` (SQLAlchemy) e `cors`, para que Models, Services e `app.py` possam importá-los sem criar importação circular.

**Usa:** —  
**Usado por:** `app.py`, `migracoes.py`, `models/avaliacao.py`, `models/base.py`, `models/cache_externo.py`, `models/checklist.py`, `models/codigo_verificacao.py`, `models/compromisso.py`, `models/despesa.py`, `models/diario.py`, `models/favorito.py`, `models/foto_lugar.py` e mais 30

### `backend/migracoes.py`  <small>(49 linhas)</small>

Sistema de migrações **não destrutivas**. Cada migração é uma função registrada em `MIGRACOES`; roda uma vez e é anotada na tabela `migracoes_aplicadas`. A única existente cria as 18 tabelas da expansão (`checkfirst=True`). Há também o utilitário `adicionar_coluna_se_ausente` para futuras evoluções. Regra: nunca apagar nem alterar dados existentes.

**Estrutura**

- **Constantes:** `TABELAS_EXPANSAO`, `MIGRACOES`
- **Função `adicionar_coluna_se_ausente(tabela, coluna, definicao_sql)`** — Adiciona uma coluna nova (sempre anulável ou com padrão) se ela ainda não existir.
- **Função `_m001_tabelas_da_expansao()`**
- **Função `aplicar_migracoes()`**

**Usa:** `extensions.py`, `models/migracao.py`  
**Usado por:** `app.py`

### `backend/seeds.py`  <small>(175 linhas)</small>

Carga inicial do banco (só roda com o banco vazio): 6 interesses e 20 lugares reais do Brasil. Na expansão ganhou `REFERENCIAS_FOTOS` (para cada lugar: título do artigo na Wikipédia por idioma, palavras que precisam aparecer no nome da foto e o raio de tolerância em km para conferir as coordenadas) e `LUGARES_FUNDO_INICIAL` (candidatos à foto da tela inicial, por ordem de preferência).

**Estrutura**

- **Constantes:** `INTERESSES`, `IMAGENS`, `LUGARES`, `REFERENCIAS_FOTOS`, `LUGARES_FUNDO_INICIAL`
- **Função `popular_banco()`** — Insere os dados iniciais apenas se o banco estiver vazio.

**Usa:** `extensions.py`, `models/interesse.py`, `models/lugar.py`  
**Usado por:** `app.py`, `services/fotos_lugar_service.py`

### `backend/sql/procedures_mysql.sql`  <small>(30 linhas)</small>

Stored Procedure `sp_ranking_destinos`, usada apenas quando o banco é MySQL. O Repository de relatório a chama; Controllers e Services nunca executam SQL direto.

---

## 3. Backend — Controllers

### `backend/controllers/__init__.py`  <small>(44 linhas)</small>

Lista `CONTROLLERS`. **É aqui que um Controller novo é ligado ao app**: `app.py` percorre a lista, instancia cada classe e chama `registrar(app)`.

**Usa:** `controllers/auth_controller.py`, `controllers/avaliacao_controller.py`, `controllers/calendario_controller.py`, `controllers/chat_controller.py`, `controllers/checklist_controller.py`, `controllers/comparador_controller.py`, `controllers/despesa_controller.py`, `controllers/diario_controller.py`, `controllers/favorito_controller.py`, `controllers/foto_controller.py`, `controllers/grupo_controller.py`, `controllers/lugar_controller.py` e mais 6  
**Usado por:** `app.py`

### `backend/controllers/auth_controller.py`  <small>(57 linhas)</small>

Rotas de autenticação. Cada ação só lê o JSON e delega ao Service. Cadastro, verificação, reenvio e login têm **limite de tentativas por IP** (10 a cada 5–10 min; 5 reenvios em 10 min), para barrar força bruta e abuso. Logout exige token.

**Rotas**

| Método | Caminho | Ação | Proteção |
|---|---|---|---|
| `POST` | `/api/auth/cadastro` | `cadastrar` | limite 10/10min |
| `POST` | `/api/auth/verificar` | `verificar` | limite 10/5min |
| `POST` | `/api/auth/reenviar-codigo` | `reenviar_codigo` | limite 5/10min |
| `POST` | `/api/auth/login` | `login` | limite 10/5min |
| `POST` | `/api/auth/logout` | `logout` | 🔒 login |

**Estrutura**

- **Classe `AuthController`** — Recebe a requisição, chama o Service e devolve a resposta HTTP.
  - `__init__()`
  - `cadastrar()`
  - `verificar()`
  - `reenviar_codigo()`
  - `login()`
  - `logout()`
  - `registrar(app)`

**Usa:** `services/autenticar_usuario_service.py`, `services/cadastrar_usuario_service.py`, `services/encerrar_sessao_service.py`, `services/reenviar_codigo_service.py`, `services/verificar_codigo_service.py`, `utils/autenticacao.py`, `utils/limite_requisicoes.py`  
**Usado por:** —

### `backend/controllers/avaliacao_controller.py`  <small>(61 linhas)</small>

Avaliações e comunidade. `GET` das avaliações de um lugar e o feed são públicos; criar/editar aceitam **JSON ou formulário com fotos** (via `dados_e_fotos()`). Limites: 10 avaliações/hora e 30 edições/hora por usuário.

**Rotas**

| Método | Caminho | Ação | Proteção |
|---|---|---|---|
| `GET` | `/api/lugares/<int:lugar_id>/avaliacoes` | `listar` |  |
| `POST` | `/api/lugares/<int:lugar_id>/avaliacoes` | `criar` | 🔒 login, limite 10/60min |
| `PUT,POST` | `/api/avaliacoes/<int:avaliacao_id>` | `editar` | 🔒 login, limite 30/60min |
| `DELETE` | `/api/avaliacoes/<int:avaliacao_id>` | `excluir` | 🔒 login |
| `DELETE` | `/api/avaliacoes/<int:avaliacao_id>/fotos/<int:foto_id>` | `remover_foto` | 🔒 login |
| `GET` | `/api/comunidade` | `comunidade` |  |

**Estrutura**

- **Classe `AvaliacaoController`**
  - `__init__()`
  - `listar(lugar_id)`
  - `criar(lugar_id)`
  - `editar(avaliacao_id)`
  - `excluir(avaliacao_id)`
  - `remover_foto(avaliacao_id, foto_id)`
  - `comunidade()`
  - `registrar(app)`

**Usa:** `services/avaliacoes_service.py`, `utils/autenticacao.py`, `utils/limite_requisicoes.py`, `utils/requisicao.py`  
**Usado por:** —

### `backend/controllers/calendario_controller.py`  <small>(45 linhas)</small>

Agenda: devolve o calendário unificado (compromissos + atividades do roteiro + conflitos) e o CRUD de compromissos.

**Rotas**

| Método | Caminho | Ação | Proteção |
|---|---|---|---|
| `GET` | `/api/viagens/<int:viagem_id>/calendario` | `calendario` | 🔒 login |
| `POST` | `/api/viagens/<int:viagem_id>/compromissos` | `criar` | 🔒 login |
| `PUT,PATCH` | `/api/compromissos/<int:compromisso_id>` | `editar` | 🔒 login |
| `DELETE` | `/api/compromissos/<int:compromisso_id>` | `excluir` | 🔒 login |

**Estrutura**

- **Classe `CalendarioController`**
  - `__init__()`
  - `calendario(viagem_id)`
  - `criar(viagem_id)`
  - `editar(compromisso_id)`
  - `excluir(compromisso_id)`
  - `registrar(app)`

**Usa:** `services/calendario_service.py`, `utils/autenticacao.py`, `utils/requisicao.py`  
**Usado por:** —

### `backend/controllers/chat_controller.py`  <small>(48 linhas)</small>

Conversa com o Vai. Na expansão: o `POST` aceita `viagem_id` (viagem em foco), tem limite de 20 mensagens/min e há as rotas `/permissoes` (ler e salvar o que o assistente pode consultar).

**Rotas**

| Método | Caminho | Ação | Proteção |
|---|---|---|---|
| `GET` | `/api/chat` | `historico` | 🔒 login |
| `POST` | `/api/chat` | `enviar` | 🔒 login, limite 20/1min |
| `GET` | `/api/chat/permissoes` | `permissoes` | 🔒 login |
| `PUT` | `/api/chat/permissoes` | `salvar_permissoes` | 🔒 login |

**Estrutura**

- **Classe `ChatController`**
  - `__init__()`
  - `historico()`
  - `enviar()`
  - `permissoes()`
  - `salvar_permissoes()`
  - `registrar(app)`

**Usa:** `services/assistente_service.py`, `services/enviar_mensagem_chat_service.py`, `services/listar_historico_chat_service.py`, `utils/autenticacao.py`, `utils/limite_requisicoes.py`  
**Usado por:** —

### `backend/controllers/checklist_controller.py`  <small>(56 linhas)</small>

Itens da mala: listar, adicionar, marcar/editar, remover, gerar sugestões e importar a lista de outra viagem.

**Rotas**

| Método | Caminho | Ação | Proteção |
|---|---|---|---|
| `GET` | `/api/viagens/<int:viagem_id>/checklist` | `listar` | 🔒 login |
| `POST` | `/api/viagens/<int:viagem_id>/checklist` | `adicionar` | 🔒 login |
| `POST` | `/api/viagens/<int:viagem_id>/checklist/sugestoes` | `sugerir` | 🔒 login |
| `POST` | `/api/viagens/<int:viagem_id>/checklist/importar` | `importar` | 🔒 login |
| `PATCH,PUT` | `/api/checklist/<int:item_id>` | `atualizar` | 🔒 login |
| `DELETE` | `/api/checklist/<int:item_id>` | `remover` | 🔒 login |

**Estrutura**

- **Classe `ChecklistController`**
  - `__init__()`
  - `listar(viagem_id)`
  - `sugerir(viagem_id)`
  - `adicionar(viagem_id)`
  - `importar(viagem_id)`
  - `atualizar(item_id)`
  - `remover(item_id)`
  - `registrar(app)`

**Usa:** `services/checklist_service.py`, `utils/autenticacao.py`, `utils/requisicao.py`  
**Usado por:** —

### `backend/controllers/comparador_controller.py`  <small>(28 linhas)</small>

`GET /api/comparador?ids=1,2,3`. Converte a lista de ids (erro 422 se algum não for número) e chama o Service; login opcional, para personalizar o match.

**Rotas**

| Método | Caminho | Ação | Proteção |
|---|---|---|---|
| `GET` | `/api/comparador` | `comparar` | limite 30/1min |

**Estrutura**

- **Classe `ComparadorController`**
  - `__init__()`
  - `comparar()`
  - `registrar(app)`

**Usa:** `services/comparador_service.py`, `utils/autenticacao.py`, `utils/erros.py`, `utils/limite_requisicoes.py`  
**Usado por:** —

### `backend/controllers/despesa_controller.py`  <small>(49 linhas)</small>

Finanças da viagem: resumo, orçamento e despesas (criar, editar, excluir). Sem regra própria — só encaminha ao `financas_service`.

**Rotas**

| Método | Caminho | Ação | Proteção |
|---|---|---|---|
| `GET` | `/api/viagens/<int:viagem_id>/financas` | `resumo` | 🔒 login |
| `PUT` | `/api/viagens/<int:viagem_id>/orcamento` | `orcamento` | 🔒 login |
| `POST` | `/api/viagens/<int:viagem_id>/despesas` | `registrar_despesa` | 🔒 login |
| `PUT,PATCH` | `/api/despesas/<int:despesa_id>` | `editar` | 🔒 login |
| `DELETE` | `/api/despesas/<int:despesa_id>` | `excluir` | 🔒 login |

**Estrutura**

- **Classe `DespesaController`**
  - `__init__()`
  - `resumo(viagem_id)`
  - `orcamento(viagem_id)`
  - `registrar_despesa(viagem_id)`
  - `editar(despesa_id)`
  - `excluir(despesa_id)`
  - `registrar(app)`

**Usa:** `services/financas_service.py`, `utils/autenticacao.py`, `utils/requisicao.py`  
**Usado por:** —

### `backend/controllers/diario_controller.py`  <small>(65 linhas)</small>

Diário de viagens: listar, criar/editar (com fotos), excluir, remover foto, estatísticas e as memórias compartilhadas de uma viagem.

**Rotas**

| Método | Caminho | Ação | Proteção |
|---|---|---|---|
| `GET` | `/api/diario` | `listar` | 🔒 login |
| `POST` | `/api/diario` | `criar` | 🔒 login, limite 40/60min |
| `GET` | `/api/diario/estatisticas` | `estatisticas` | 🔒 login |
| `PUT,POST` | `/api/diario/<int:registro_id>` | `editar` | 🔒 login, limite 60/60min |
| `DELETE` | `/api/diario/<int:registro_id>` | `excluir` | 🔒 login |
| `DELETE` | `/api/diario/<int:registro_id>/fotos/<int:foto_id>` | `remover_foto` | 🔒 login |
| `GET` | `/api/viagens/<int:viagem_id>/diario` | `da_viagem` | 🔒 login |

**Estrutura**

- **Classe `DiarioController`**
  - `__init__()`
  - `listar()`
  - `criar()`
  - `editar(registro_id)`
  - `excluir(registro_id)`
  - `remover_foto(registro_id, foto_id)`
  - `estatisticas()`
  - `da_viagem(viagem_id)`
  - `registrar(app)`

**Usa:** `services/diario_service.py`, `utils/autenticacao.py`, `utils/limite_requisicoes.py`, `utils/requisicao.py`  
**Usado por:** —

### `backend/controllers/favorito_controller.py`  <small>(38 linhas)</small>

Salvar, listar e remover favoritos; todas as rotas exigem login.

**Rotas**

| Método | Caminho | Ação | Proteção |
|---|---|---|---|
| `GET` | `/api/favoritos` | `listar` | 🔒 login |
| `POST` | `/api/favoritos` | `salvar` | 🔒 login |
| `DELETE` | `/api/favoritos/<int:lugar_id>` | `remover` | 🔒 login |

**Estrutura**

- **Classe `FavoritoController`**
  - `__init__()`
  - `listar()`
  - `salvar()`
  - `remover(lugar_id)`
  - `registrar(app)`

**Usa:** `services/listar_favoritos_service.py`, `services/remover_favorito_service.py`, `services/salvar_favorito_service.py`, `utils/autenticacao.py`  
**Usado por:** —

### `backend/controllers/foto_controller.py`  <small>(42 linhas)</small>

Três responsabilidades: fotos verificadas de um lugar, dados do fundo da tela inicial (com cache de 10 min) e **entrega de uploads**. `arquivo()` só serve o arquivo se a assinatura HMAC e a validade da URL forem válidas e responde 404 caso contrário; envia `nosniff` e cache privado.

**Rotas**

| Método | Caminho | Ação | Proteção |
|---|---|---|---|
| `GET` | `/api/lugares/<int:lugar_id>/fotos` | `fotos_do_lugar` |  |
| `GET` | `/api/vitrine/fundo` | `fundo_inicial` |  |
| `GET` | `/api/arquivos/<subpasta>/<nome>` | `arquivo` |  |

**Estrutura**

- **Classe `FotoController`**
  - `__init__()`
  - `fotos_do_lugar(lugar_id)`
  - `fundo_inicial()`
  - `arquivo(subpasta, nome)` — Serve uploads só com URL assinada e válida (gerada após checar permissão).
  - `registrar(app)`

**Usa:** `services/fotos_lugar_service.py`, `utils/arquivos.py`  
**Usado por:** —

### `backend/controllers/grupo_controller.py`  <small>(87 linhas)</small>

Viagens em grupo: participantes, convites (limite de 20 a cada 10 min), troca de papel, remover/sair, sugestões (limite 30 a cada 10 min), voto e decisão.

**Rotas**

| Método | Caminho | Ação | Proteção |
|---|---|---|---|
| `GET` | `/api/viagens/<int:viagem_id>/participantes` | `participantes` | 🔒 login |
| `POST` | `/api/viagens/<int:viagem_id>/participantes` | `convidar` | 🔒 login, limite 20/10min |
| `PATCH,PUT` | `/api/viagens/<int:viagem_id>/participantes/<int:participante_id>` | `alterar_papel` | 🔒 login |
| `DELETE` | `/api/viagens/<int:viagem_id>/participantes/<int:participante_id>` | `remover` | 🔒 login |
| `GET` | `/api/convites` | `convites` | 🔒 login |
| `POST` | `/api/convites/<int:convite_id>/aceitar` | `aceitar` | 🔒 login |
| `POST` | `/api/convites/<int:convite_id>/recusar` | `recusar` | 🔒 login |
| `GET` | `/api/viagens/<int:viagem_id>/sugestoes` | `sugestoes` | 🔒 login |
| `POST` | `/api/viagens/<int:viagem_id>/sugestoes` | `sugerir` | 🔒 login, limite 30/10min |
| `POST` | `/api/sugestoes/<int:sugestao_id>/voto` | `votar` | 🔒 login |
| `POST` | `/api/sugestoes/<int:sugestao_id>/decisao` | `decidir` | 🔒 login |

**Estrutura**

- **Classe `GrupoController`**
  - `__init__()`
  - `participantes(viagem_id)`
  - `convidar(viagem_id)`
  - `alterar_papel(viagem_id, participante_id)`
  - `remover(viagem_id, participante_id)`
  - `convites()`
  - `aceitar(convite_id)`
  - `recusar(convite_id)`
  - `sugestoes(viagem_id)`
  - `sugerir(viagem_id)`
  - `votar(sugestao_id)`
  - `decidir(sugestao_id)`
  - `registrar(app)`

**Usa:** `services/grupo_service.py`, `utils/autenticacao.py`, `utils/limite_requisicoes.py`, `utils/requisicao.py`  
**Usado por:** —

### `backend/controllers/lugar_controller.py`  <small>(61 linhas)</small>

Catálogo de lugares: listar, buscar com filtros, recomendações personalizadas (exige login) e detalhe. Usa `usuario_do_token()` — login **opcional** — para marcar favoritos e calcular match quando há usuário.

**Rotas**

| Método | Caminho | Ação | Proteção |
|---|---|---|---|
| `GET` | `/api/lugares` | `listar` |  |
| `GET` | `/api/lugares/busca` | `buscar` |  |
| `GET` | `/api/lugares/recomendacoes` | `recomendacoes` | 🔒 login |
| `GET` | `/api/lugares/<int:lugar_id>` | `detalhar` |  |

**Estrutura**

- **Classe `LugarController`**
  - `__init__()`
  - `listar()`
  - `buscar()`
  - `recomendacoes()`
  - `detalhar(lugar_id)`
  - `registrar(app)`

**Usa:** `services/buscar_lugares_service.py`, `services/listar_lugares_service.py`, `services/obter_lugar_service.py`, `services/recomendar_lugares_service.py`, `utils/autenticacao.py`  
**Usado por:** —

### `backend/controllers/mapa_controller.py`  <small>(44 linhas)</small>

Dados para o mapa: configuração dos tiles, todos os lugares, mapa de uma viagem (exige login) e proximidades de um lugar (limite de 30/min porque pode consultar o OpenStreetMap).

**Rotas**

| Método | Caminho | Ação | Proteção |
|---|---|---|---|
| `GET` | `/api/mapa/config` | `configuracao` |  |
| `GET` | `/api/mapa/lugares` | `lugares` |  |
| `GET` | `/api/viagens/<int:viagem_id>/mapa` | `viagem` | 🔒 login |
| `GET` | `/api/lugares/<int:lugar_id>/proximidades` | `proximidades` | limite 30/1min |

**Estrutura**

- **Classe `MapaController`**
  - `__init__()`
  - `configuracao()`
  - `lugares()`
  - `viagem(viagem_id)`
  - `proximidades(lugar_id)`
  - `registrar(app)`

**Usa:** `services/mapa_service.py`, `utils/autenticacao.py`, `utils/limite_requisicoes.py`  
**Usado por:** —

### `backend/controllers/preferencia_controller.py`  <small>(34 linhas)</small>

Interesses, orçamento e cidade. `/opcoes` é público (a tela de interesses usa antes de existir preferência); `GET` e `PUT/POST` exigem login.

**Rotas**

| Método | Caminho | Ação | Proteção |
|---|---|---|---|
| `GET` | `/api/preferencias/opcoes` | `opcoes` |  |
| `GET` | `/api/preferencias` | `minhas` | 🔒 login |
| `PUT,POST` | `/api/preferencias` | `salvar` | 🔒 login |

**Estrutura**

- **Classe `PreferenciaController`**
  - `__init__()`
  - `opcoes()`
  - `minhas()`
  - `salvar()`
  - `registrar(app)`

**Usa:** `services/listar_interesses_service.py`, `services/salvar_preferencias_service.py`, `utils/autenticacao.py`  
**Usado por:** —

### `backend/controllers/relatorio_controller.py`  <small>(22 linhas)</small>

`GET /api/relatorios/destinos`: ranking dos mais salvos e estatísticas gerais (público).

**Rotas**

| Método | Caminho | Ação | Proteção |
|---|---|---|---|
| `GET` | `/api/relatorios/destinos` | `destinos` |  |

**Estrutura**

- **Classe `RelatorioController`**
  - `__init__()`
  - `destinos()`
  - `registrar(app)`

**Usa:** `services/gerar_relatorio_service.py`  
**Usado por:** —

### `backend/controllers/roteiro_controller.py`  <small>(89 linhas)</small>

Rotas de roteiros e atividades (`/viagens/<id>/roteiros`, `/roteiros/<id>`, `/atividades/<id>`). Gerar roteiro tem limite de 8 por minuto, porque pode acionar a IA e consultas externas. A rota `/ordem` recebe a nova posição de várias atividades de uma vez.

**Rotas**

| Método | Caminho | Ação | Proteção |
|---|---|---|---|
| `GET` | `/api/viagens/<int:viagem_id>/roteiros` | `listar` | 🔒 login |
| `POST` | `/api/viagens/<int:viagem_id>/roteiros` | `criar_manual` | 🔒 login |
| `POST` | `/api/viagens/<int:viagem_id>/roteiros/gerar` | `gerar` | 🔒 login, limite 8/1min |
| `GET` | `/api/roteiros/<int:roteiro_id>` | `detalhar` | 🔒 login |
| `DELETE` | `/api/roteiros/<int:roteiro_id>` | `excluir` | 🔒 login |
| `POST` | `/api/roteiros/<int:roteiro_id>/duplicar` | `duplicar` | 🔒 login |
| `POST` | `/api/roteiros/<int:roteiro_id>/ativar` | `ativar` | 🔒 login |
| `PUT` | `/api/roteiros/<int:roteiro_id>/ordem` | `reorganizar` | 🔒 login |
| `POST` | `/api/roteiros/<int:roteiro_id>/atividades` | `adicionar_atividade` | 🔒 login |
| `PUT,PATCH` | `/api/atividades/<int:atividade_id>` | `editar_atividade` | 🔒 login |
| `DELETE` | `/api/atividades/<int:atividade_id>` | `excluir_atividade` | 🔒 login |

**Estrutura**

- **Classe `RoteiroController`**
  - `__init__()`
  - `listar(viagem_id)`
  - `gerar(viagem_id)`
  - `criar_manual(viagem_id)`
  - `detalhar(roteiro_id)`
  - `duplicar(roteiro_id)`
  - `ativar(roteiro_id)`
  - `excluir(roteiro_id)`
  - `reorganizar(roteiro_id)`
  - `adicionar_atividade(roteiro_id)`
  - `editar_atividade(atividade_id)`
  - `excluir_atividade(atividade_id)`
  - `registrar(app)`

**Usa:** `services/roteiros_service.py`, `utils/autenticacao.py`, `utils/limite_requisicoes.py`, `utils/requisicao.py`  
**Usado por:** —

### `backend/controllers/usuario_controller.py`  <small>(22 linhas)</small>

Uma rota: `GET /api/usuarios/eu`, o perfil do usuário logado (dados, preferências e total de salvos).

**Rotas**

| Método | Caminho | Ação | Proteção |
|---|---|---|---|
| `GET` | `/api/usuarios/eu` | `perfil` | 🔒 login |

**Estrutura**

- **Classe `UsuarioController`**
  - `__init__()`
  - `perfil()`
  - `registrar(app)`

**Usa:** `services/obter_perfil_service.py`, `utils/autenticacao.py`  
**Usado por:** —

### `backend/controllers/viagem_controller.py`  <small>(50 linhas)</small>

CRUD de viagens em `/api/viagens`. Criar tem limite de 30 por hora. Toda a validação e a checagem de permissão estão nos Services.

**Rotas**

| Método | Caminho | Ação | Proteção |
|---|---|---|---|
| `GET` | `/api/viagens` | `listar` | 🔒 login |
| `POST` | `/api/viagens` | `criar` | 🔒 login, limite 30/60min |
| `GET` | `/api/viagens/<int:viagem_id>` | `detalhar` | 🔒 login |
| `PUT,PATCH` | `/api/viagens/<int:viagem_id>` | `editar` | 🔒 login |
| `DELETE` | `/api/viagens/<int:viagem_id>` | `excluir` | 🔒 login |

**Estrutura**

- **Classe `ViagemController`**
  - `__init__()`
  - `listar()`
  - `criar()`
  - `detalhar(viagem_id)`
  - `editar(viagem_id)`
  - `excluir(viagem_id)`
  - `registrar(app)`

**Usa:** `services/viagens_service.py`, `utils/autenticacao.py`, `utils/limite_requisicoes.py`, `utils/requisicao.py`  
**Usado por:** —

---

## 4. Backend — Services

### `backend/services/__init__.py`  <small>(34 linhas)</small>

Apenas a documentação (docstring) com a lista dos casos de uso e das integrações externas.

### `backend/services/assistente_local_service.py`  <small>(188 linhas)</small>

Motor de resposta sem IA externa (reserva do chat). Reconhece intenções por palavras-chave (roteiro, época, preço, praia, comida, proximidade...). Na expansão responde também sobre viagem, gastos, agenda/conflitos e mala — mas só se o contexto trouxer esses dados (ou seja, se houve autorização). `_brl` formata valores em reais.

**Estrutura**

- **Função `_normalizar(texto)`**
- **Função `_brl(valor)`**
- **Classe `AssistenteLocalService`**
  - `executar(pergunta, contexto)`
  - `_responder_sobre_viagem(texto, viagem, contexto)` — Respostas que usam os dados da viagem — só existem se o usuário autorizou.

**Usa:** —  
**Usado por:** `services/gemini_service.py`, `tests/test_regras.py`

### `backend/services/assistente_service.py`  <small>(144 linhas)</small>

Expansão do Vai. **Permissões** (favoritos, viagens/roteiro/agenda, finanças, diário), todas desligadas por padrão; **contexto** (`MontarContextoAssistenteService`) que só inclui o que foi autorizado — escolher uma viagem no chat autoriza os dados dela; e **ações** (`SugerirAcoesAssistenteService`) que transformam intenções em botões (criar viagem, gerar roteiro, abrir gastos/agenda/checklist, comparar).

**Estrutura**

- **Função `_normalizar(texto)`**
- **Classe `ObterPermissoesAssistenteService`**
  - `executar(usuario)`
- **Classe `SalvarPermissoesAssistenteService`**
  - `executar(usuario, dados)`
- **Classe `MontarContextoAssistenteService`**
  - `__init__(repositorio, autorizacao)`
  - `executar(usuario, viagem_id)`
- **Classe `SugerirAcoesAssistenteService`** — Detecta intenções simples na pergunta e devolve atalhos para as telas certas.
  - `executar(pergunta, contexto)`

**Usa:** `models/diario.py`, `models/lugar.py`, `models/permissao_assistente.py`, `repositories/favorito_repository.py`, `repositories/viagem_repository.py`, `services/autorizacao_viagem_service.py`, `services/calendario_service.py`, `services/financas_service.py`, `utils/datas.py`, `utils/validadores.py`  
**Usado por:** `controllers/chat_controller.py`, `services/enviar_mensagem_chat_service.py`

### `backend/services/autenticar_usuario_service.py`  <small>(31 linhas)</small>

Login: confere e-mail e hash da senha com mensagem **genérica** (não revela se o e-mail existe), bloqueia contas não verificadas e gera um novo token.

**Estrutura**

- **Classe `AutenticarUsuarioService`**
  - `executar(dados)`

**Usa:** `models/usuario.py`, `utils/erros.py`, `utils/validadores.py`  
**Usado por:** `controllers/auth_controller.py`

### `backend/services/autorizacao_viagem_service.py`  <small>(39 linhas)</small>

**O guarda das viagens.** `executar(viagem_id, usuario, nivel)` devolve a viagem ou lança erro. Níveis: `leitura` (proprietário, editor, viajante), `edicao` (proprietário, editor) e `proprietario`. Quem não participa — ou só foi convidado e ainda não aceitou — recebe **404**, para não revelar que a viagem existe; quem participa sem nível suficiente recebe 403.

**Estrutura**

- **Constantes:** `NIVEIS`, `MENSAGENS`
- **Classe `AutorizacaoViagemService`**
  - `executar(viagem_id, usuario, nivel)`
  - `pode(viagem, usuario, nivel)`

**Usa:** `models/viagem.py`, `utils/erros.py`  
**Usado por:** `services/assistente_service.py`, `services/calendario_service.py`, `services/checklist_service.py`, `services/diario_service.py`, `services/financas_service.py`, `services/grupo_service.py`, `services/mapa_service.py`, `services/roteiros_service.py`, `services/viagens_service.py`

### `backend/services/avaliacoes_service.py`  <small>(194 linhas)</small>

Avaliações com regras anti-manipulação: **uma por pessoa e lugar**, nota 1–5, comentário de 10 a 2000 caracteres, data de visita não pode ser futura. A média exibida considera só avaliações da comunidade. O selo **"viagem verificada"** é calculado a partir de uma viagem concluída do autor que passou pelo lugar. Fotos inválidas anulam o envio inteiro (sem arquivos órfãos).

**Estrutura**

- **Função `_lugar(lugar_id)`**
- **Função `_validar(dados, atual)`**
- **Função `_verificar_experiencia(avaliacao, repositorio)`**
- **Função `_salvar_fotos(avaliacao, arquivos_enviados)`**
- **Função `_avaliacao_propria(avaliacao_id, usuario)`**
- **Classe `ListarAvaliacoesLugarService`**
  - `executar(lugar_id, usuario, ordenar)`
- **Classe `CriarAvaliacaoService`**
  - `__init__(repositorio)`
  - `executar(lugar_id, usuario, dados, fotos)`
- **Classe `EditarAvaliacaoService`**
  - `__init__(repositorio)`
  - `executar(avaliacao_id, usuario, dados, fotos)`
- **Classe `ExcluirAvaliacaoService`**
  - `executar(avaliacao_id, usuario)`
- **Classe `RemoverFotoAvaliacaoService`**
  - `executar(avaliacao_id, foto_id, usuario)`
- **Classe `ListarComunidadeService`** — Feed da comunidade: avaliações recentes e relatos públicos do diário.
  - `executar(usuario, limite)`

**Usa:** `config.py`, `extensions.py`, `models/avaliacao.py`, `models/diario.py`, `models/lugar.py`, `repositories/viagem_repository.py`, `utils/arquivos.py`, `utils/datas.py`, `utils/erros.py`, `utils/validadores.py`  
**Usado por:** `controllers/avaliacao_controller.py`

### `backend/services/buscar_lugares_service.py`  <small>(49 linhas)</small>

Busca por texto, categoria, preço, estado e nota; ordena por nota, populares, preço, nome ou match.

**Estrutura**

- **Classe `BuscarLugaresService`**
  - `__init__(repositorio, repositorio_favoritos, servico_match)`
  - `executar(usuario, filtros)`

**Usa:** `repositories/favorito_repository.py`, `repositories/lugar_repository.py`, `services/calcular_match_service.py`  
**Usado por:** `controllers/lugar_controller.py`

### `backend/services/cadastrar_usuario_service.py`  <small>(46 linhas)</small>

Valida nome, e-mail e senha; cria o usuário (ou reaproveita um cadastro não concluído), emite o código de 6 dígitos e o envia por e-mail. Em modo debug sem SMTP devolve o código na resposta para facilitar testes.

**Estrutura**

- **Classe `CadastrarUsuarioService`** — Valida os dados, cria o usuário e dispara o código de verificação.
  - `__init__(servico_email)`
  - `executar(dados)`

**Usa:** `config.py`, `models/codigo_verificacao.py`, `models/usuario.py`, `services/envio_email_service.py`, `utils/erros.py`, `utils/validadores.py`  
**Usado por:** `controllers/auth_controller.py`

### `backend/services/calcular_match_service.py`  <small>(53 linhas)</small>

Regra de compatibilidade (35–99%): base 44 + interesse (+24/−6) + nota + aderência ao orçamento + proximidade da cidade do usuário + popularidade (máx. +5). Reutilizada por listagem, busca, recomendações, comparador e chat.

**Estrutura**

- **Classe `CalcularMatchService`**
  - `executar(lugar, preferencia, distancia)`
  - `distancia_para(lugar, preferencia)`

**Usa:** `utils/geo.py`  
**Usado por:** `services/buscar_lugares_service.py`, `services/comparador_service.py`, `services/listar_favoritos_service.py`, `services/listar_lugares_service.py`, `services/obter_lugar_service.py`, `services/recomendar_lugares_service.py`, `tests/test_regras.py`

### `backend/services/calendario_service.py`  <small>(149 linhas)</small>

Junta compromissos e atividades **com horário** do roteiro principal numa agenda única, ordena e **detecta conflitos** (intervalos que se sobrepõem). Atividades sem horário vão em `sem_horario`. Compromissos precisam estar no período da viagem (±1 dia).

**Estrutura**

- **Constantes:** `DURACAO_PADRAO_ATIVIDADE`
- **Função `detectar_conflitos(eventos)`** — Pares de eventos cujos intervalos se sobrepõem (ordenados por início).
- **Classe `ObterCalendarioService`**
  - `__init__(autorizacao)`
  - `executar(viagem_id, usuario)`
- **Função `_validar(dados, viagem, atual)`**
- **Função `_compromisso_autorizado(compromisso_id, usuario, autorizacao)`**
- **Classe `CriarCompromissoService`**
  - `__init__(autorizacao)`
  - `executar(viagem_id, usuario, dados)`
- **Classe `EditarCompromissoService`**
  - `__init__(autorizacao)`
  - `executar(compromisso_id, usuario, dados)`
- **Classe `ExcluirCompromissoService`**
  - `__init__(autorizacao)`
  - `executar(compromisso_id, usuario)`

**Usa:** `extensions.py`, `models/compromisso.py`, `services/autorizacao_viagem_service.py`, `utils/erros.py`, `utils/validadores.py`  
**Usado por:** `controllers/calendario_controller.py`, `services/assistente_service.py`

### `backend/services/checklist_service.py`  <small>(217 linhas)</small>

Gera sugestões combinando uma lista base, itens por interesse (praia, trilha...), por tipo de viagem e pela duração; evita duplicar (compara o texto normalizado sem acentos); só sugere conferir passaporte quando o destino não parece nacional. Também adiciona, marca, remove e importa itens de outra viagem (desmarcados). Limite de 300 itens.

**Estrutura**

- **Constantes:** `MAXIMO_ITENS`, `BASE`, `POR_INTERESSE`, `POR_TIPO`
- **Função `_chave(texto)`**
- **Função `sugerir_itens(viagem, interesses)`**
- **Função `_resposta(viagem, usuario)`**
- **Função `_item_autorizado(item_id, usuario, autorizacao)`**
- **Classe `ListarChecklistService`**
  - `__init__(autorizacao)`
  - `executar(viagem_id, usuario)`
- **Classe `GerarSugestoesChecklistService`**
  - `__init__(autorizacao)`
  - `executar(viagem_id, usuario)`
- **Classe `AdicionarItemChecklistService`**
  - `__init__(autorizacao)`
  - `executar(viagem_id, usuario, dados)`
- **Classe `AtualizarItemChecklistService`**
  - `__init__(autorizacao)`
  - `executar(item_id, usuario, dados)`
- **Classe `RemoverItemChecklistService`**
  - `__init__(autorizacao)`
  - `executar(item_id, usuario)`
- **Classe `ImportarChecklistService`** — Reaproveita a lista de outra viagem à qual o usuário tem acesso (itens desmarcados).
  - `__init__(autorizacao)`
  - `executar(viagem_id, usuario, dados)`

**Usa:** `extensions.py`, `models/checklist.py`, `services/autorizacao_viagem_service.py`, `utils/erros.py`, `utils/validadores.py`  
**Usado por:** `controllers/checklist_controller.py`

### `backend/services/comparador_service.py`  <small>(107 linhas)</small>

Compara 2–3 lugares. Cada critério usa só dado existente: catálogo, média da comunidade, atrações num raio de 60 km, pontos OSM já conhecidos, clima (se disponível), distância e match. `_destaques` marca o vencedor de cada critério quando há diferença real.

**Estrutura**

- **Constantes:** `RAIO_ATRACOES_KM`, `MAXIMO`
- **Classe `CompararDestinosService`**
  - `__init__(servico_match, servico_clima, servico_pontos)`
  - `executar(ids, usuario, incluir_clima)`

**Usa:** `extensions.py`, `models/avaliacao.py`, `models/interesse.py`, `models/lugar.py`, `repositories/favorito_repository.py`, `services/calcular_match_service.py`, `services/integracoes/clima_service.py`, `services/integracoes/pontos_interesse_service.py`, `utils/erros.py`, `utils/geo.py`  
**Usado por:** `controllers/comparador_controller.py`

### `backend/services/diario_service.py`  <small>(210 linhas)</small>

Registros do diário (data não pode ser futura; visibilidade privado/participantes/público; "participantes" exige viagem vinculada), linha do tempo por ano e estatísticas (viagens concluídas, dias, destinos, estados, fotos, nota média, categoria favorita).

**Estrutura**

- **Função `_validar(dados, usuario, autorizacao, atual)`**
- **Função `_salvar_fotos(registro, enviados)`**
- **Função `_registro_proprio(registro_id, usuario)`**
- **Classe `ListarDiarioService`**
  - `executar(usuario)`
- **Classe `ListarDiarioDaViagemService`** — Registros compartilhados com os participantes (e os próprios) de uma viagem.
  - `__init__(autorizacao)`
  - `executar(viagem_id, usuario)`
- **Classe `CriarRegistroDiarioService`**
  - `__init__(autorizacao)`
  - `executar(usuario, dados, fotos)`
- **Classe `EditarRegistroDiarioService`**
  - `__init__(autorizacao)`
  - `executar(registro_id, usuario, dados, fotos)`
- **Classe `ExcluirRegistroDiarioService`**
  - `executar(registro_id, usuario)`
- **Classe `RemoverFotoDiarioService`**
  - `executar(registro_id, foto_id, usuario)`
- **Classe `EstatisticasViagemService`**
  - `__init__(repositorio)`
  - `executar(usuario)`

**Usa:** `config.py`, `extensions.py`, `models/diario.py`, `models/lugar.py`, `repositories/viagem_repository.py`, `services/autorizacao_viagem_service.py`, `utils/arquivos.py`, `utils/datas.py`, `utils/erros.py`, `utils/validadores.py`  
**Usado por:** `controllers/diario_controller.py`

### `backend/services/encerrar_sessao_service.py`  <small>(9 linhas)</small>

Logout: apaga o token do usuário, invalidando a sessão.

**Estrutura**

- **Classe `EncerrarSessaoService`**
  - `executar(usuario)`

**Usa:** —  
**Usado por:** `controllers/auth_controller.py`

### `backend/services/enviar_mensagem_chat_service.py`  <small>(68 linhas)</small>

Orquestra uma pergunta ao Vai: valida o texto (máx. 1000 caracteres), **valida o acesso à viagem em foco antes de gravar a pergunta**, monta o contexto (perfil + recomendações + só os dados que o usuário autorizou), consulta a IA, grava a resposta e devolve também as **ações sugeridas**.

**Estrutura**

- **Classe `EnviarMensagemChatService`** — Monta o contexto (perfil + dados autorizados pelo usuário) e consulta o Vai.
  - `__init__(servico_ia, servico_recomendacao, servico_listagem, servico_contexto, servico_acoes)`
  - `executar(usuario, texto, viagem_id)`

**Usa:** `models/mensagem_chat.py`, `models/preferencia.py`, `services/assistente_service.py`, `services/gemini_service.py`, `services/listar_lugares_service.py`, `services/recomendar_lugares_service.py`, `utils/erros.py`  
**Usado por:** `controllers/chat_controller.py`

### `backend/services/envio_email_service.py`  <small>(48 linhas)</small>

Envia e-mails por SMTP; sem SMTP configurado apenas imprime no terminal (modo `console`). Usado no código de verificação e nos convites de viagem.

**Estrutura**

- **Classe `EnvioEmailService`** — Caso de uso: enviar um e-mail transacional.
  - `__init__(config)`
  - `executar(destinatario, assunto, corpo)`
  - `enviar_codigo(usuario, codigo)`

**Usa:** `config.py`  
**Usado por:** `services/cadastrar_usuario_service.py`, `services/grupo_service.py`, `services/reenviar_codigo_service.py`

### `backend/services/financas_service.py`  <small>(186 linhas)</small>

Resumo financeiro (`montar`): orçamento, gasto, saldo, % usado, por pessoa e por dia, categorias com planejado × gasto, quem pagou e **alertas** (≥ 80% do orçamento, ultrapassado, categoria acima do planejado). Dinheiro é guardado em **centavos** (inteiros) para evitar erro de arredondamento. Valida que quem pagou participa da viagem.

**Estrutura**

- **Constantes:** `LIMITE_ALERTA`
- **Função `_reais(centavos)`**
- **Classe `ResumoFinanceiroService`**
  - `__init__(autorizacao)`
  - `executar(viagem_id, usuario)`
  - `montar(viagem, usuario)`
- **Classe `DefinirOrcamentoService`**
  - `__init__(autorizacao)`
  - `executar(viagem_id, usuario, dados)`
- **Função `_validar_despesa(dados, viagem, atual)`**
- **Função `_despesa_autorizada(despesa_id, usuario, autorizacao)`**
- **Classe `RegistrarDespesaService`**
  - `__init__(autorizacao)`
  - `executar(viagem_id, usuario, dados)`
- **Classe `EditarDespesaService`**
  - `__init__(autorizacao)`
  - `executar(despesa_id, usuario, dados)`
- **Classe `ExcluirDespesaService`**
  - `__init__(autorizacao)`
  - `executar(despesa_id, usuario)`

**Usa:** `extensions.py`, `models/despesa.py`, `services/autorizacao_viagem_service.py`, `utils/erros.py`, `utils/validadores.py`  
**Usado por:** `controllers/despesa_controller.py`, `services/assistente_service.py`

### `backend/services/fotos_lugar_service.py`  <small>(214 linhas)</small>

Sincroniza fotos reais (`SincronizarFotosService`), faz a curadoria (`CurarFotoService`: aprovar, rejeitar, definir principal; ao aprovar do Unsplash registra o uso, como a API exige), escolhe a foto do fundo (`ObterFundoInicialService`: manifesto local → melhor paisagem verificada → nada) e inicia a sincronização em segundo plano.

**Estrutura**

- **Constantes:** `PASTA_FUNDO`, `CAMPOS_FOTO`
- **Classe `ListarFotosLugarService`**
  - `executar(lugar_id)`
- **Classe `SincronizarFotosService`** — Busca candidatas nas fontes e grava em FotoLugar (sem duplicar URLs).
  - `__init__(provedores)`
  - `executar(lugar_ids, fontes, somente_sem_fotos, limite_por_lugar)`
  - `gravar(lugar, candidatas)`
- **Classe `CurarFotoService`** — Curadoria manual (CLI tools/fotos.py): aprovar, rejeitar e escolher a principal.
  - `__init__(unsplash)`
  - `aprovar(foto_id, criterio)`
  - `rejeitar(foto_id)`
  - `definir_principal(foto_id)`
- **Classe `ObterFundoInicialService`** — Fotografia real para o fundo da tela inicial (feature 12).
  - `executar()`
- **Função `sincronizar_em_segundo_plano(app)`** — Executa a sincronização Wikimedia numa thread, sem atrasar a subida do servidor.

**Usa:** `config.py`, `extensions.py`, `models/foto_lugar.py`, `models/lugar.py`, `seeds.py`, `services/integracoes/fotos_pexels_service.py`, `services/integracoes/fotos_unsplash_service.py`, `services/integracoes/fotos_wikimedia_service.py`, `utils/erros.py`  
**Usado por:** `app.py`, `controllers/foto_controller.py`, `tests/test_funcionalidades.py`, `tools/fotos.py`

### `backend/services/gemini_service.py`  <small>(153 linhas)</small>

Integração com o Google Gemini. `executar` responde ao chat (cai no motor local se não houver chave ou se a API falhar); `gerar_json` pede resposta estruturada para os roteiros. O prompt inclui, **apenas com autorização**, viagens, roteiro, agenda, gastos, checklist, favoritos e diário, e manda a IA não inventar preços, horários, disponibilidade ou estabelecimentos.

**Estrutura**

- **Constantes:** `URL_BASE`, `INSTRUCAO`, `INSTRUCAO_PLANEJADOR`
- **Classe `GeminiService`**
  - `__init__(config, servico_local)`
  - `configurado()`
  - `executar(pergunta, contexto, historico)`
  - `gerar_json(prompt, max_tokens)` — Pede uma resposta estruturada (JSON). Devolve dict/list ou None em qualquer falha.

**Usa:** `config.py`, `services/assistente_local_service.py`  
**Usado por:** `services/enviar_mensagem_chat_service.py`, `services/roteiro_inteligente_service.py`

### `backend/services/gerar_relatorio_service.py`  <small>(18 linhas)</small>

Junta ranking, interesses mais escolhidos, lugares por categoria e estatísticas para o relatório.

**Estrutura**

- **Classe `GerarRelatorioService`**
  - `__init__(repositorio, repositorio_lugares)`
  - `executar(limite)`

**Usa:** `repositories/lugar_repository.py`, `repositories/relatorio_repository.py`  
**Usado por:** `controllers/relatorio_controller.py`

### `backend/services/grupo_service.py`  <small>(250 linhas)</small>

Convites (só para contas verificadas; limite de 30 participantes), aceitar/recusar, mudar papel, remover ou sair. Os e-mails dos participantes só aparecem para o organizador. Sugestões: o autor já vota a favor; votos únicos por pessoa; ao aprovar, a sugestão vira atividade do roteiro principal.

**Estrutura**

- **Constantes:** `MAXIMO_PARTICIPANTES`
- **Função `_participantes(viagem, usuario)`**
- **Classe `ListarParticipantesService`**
  - `__init__(autorizacao)`
  - `executar(viagem_id, usuario)`
- **Classe `ConvidarParticipanteService`**
  - `__init__(autorizacao, servico_email)`
  - `executar(viagem_id, usuario, dados)`
- **Classe `ListarConvitesService`**
  - `executar(usuario)`
- **Classe `ResponderConviteService`**
  - `executar(convite_id, usuario, aceitar)`
- **Função `_participante_da_viagem(viagem, participante_id)`**
- **Classe `AlterarPapelService`**
  - `__init__(autorizacao)`
  - `executar(viagem_id, participante_id, usuario, dados)`
- **Classe `RemoverParticipanteService`** — O organizador remove qualquer participante; um participante pode sair sozinho.
  - `__init__(autorizacao)`
  - `executar(viagem_id, participante_id, usuario)`
- **Função `_sugestoes(viagem, usuario)`**
- **Função `_sugestao_autorizada(sugestao_id, usuario, autorizacao, nivel)`**
- **Classe `ListarSugestoesService`**
  - `__init__(autorizacao)`
  - `executar(viagem_id, usuario)`
- **Classe `CriarSugestaoService`**
  - `__init__(autorizacao)`
  - `executar(viagem_id, usuario, dados)`
- **Classe `VotarSugestaoService`**
  - `__init__(autorizacao)`
  - `executar(sugestao_id, usuario, dados)`
- **Classe `DecidirSugestaoService`** — Organizador/editores aprovam (vira atividade do roteiro principal) ou rejeitam.
  - `__init__(autorizacao)`
  - `executar(sugestao_id, usuario, dados)`

**Usa:** `extensions.py`, `models/lugar.py`, `models/roteiro.py`, `models/sugestao.py`, `models/usuario.py`, `models/viagem.py`, `services/autorizacao_viagem_service.py`, `services/envio_email_service.py`, `services/roteiros_service.py`, `utils/datas.py`, `utils/erros.py`, `utils/validadores.py`  
**Usado por:** `controllers/grupo_controller.py`

### `backend/services/listar_favoritos_service.py`  <small>(27 linhas)</small>

Lista os favoritos com match e distância.

**Estrutura**

- **Classe `ListarFavoritosService`**
  - `__init__(repositorio, servico_match)`
  - `executar(usuario)`

**Usa:** `repositories/favorito_repository.py`, `services/calcular_match_service.py`  
**Usado por:** `controllers/favorito_controller.py`

### `backend/services/listar_historico_chat_service.py`  <small>(24 linhas)</small>

Histórico da conversa; cria a saudação do Vai na primeira vez e devolve os atalhos de perguntas rápidas.

**Estrutura**

- **Classe `ListarHistoricoChatService`**
  - `executar(usuario)`

**Usa:** `models/mensagem_chat.py`  
**Usado por:** `controllers/chat_controller.py`

### `backend/services/listar_interesses_service.py`  <small>(16 linhas)</small>

Devolve os interesses, as faixas de orçamento e as cidades disponíveis para a tela de interesses.

**Estrutura**

- **Classe `ListarInteressesService`**
  - `executar()`

**Usa:** `models/interesse.py`, `models/preferencia.py`, `utils/geo.py`  
**Usado por:** `controllers/preferencia_controller.py`

### `backend/services/listar_lugares_service.py`  <small>(29 linhas)</small>

Lista lugares com match, distância e marca de favorito para o usuário (ou sem personalização se não houver login).

**Estrutura**

- **Classe `ListarLugaresService`**
  - `__init__(repositorio, repositorio_favoritos, servico_match)`
  - `executar(usuario, categoria, limite)`

**Usa:** `repositories/favorito_repository.py`, `repositories/lugar_repository.py`, `services/calcular_match_service.py`  
**Usado por:** `controllers/lugar_controller.py`, `services/enviar_mensagem_chat_service.py`

### `backend/services/mapa_service.py`  <small>(103 linhas)</small>

Dados do mapa: configuração dos tiles, todos os lugares, mapa de uma viagem (destino, atividades numeradas por dia, compromissos, trajetos e trechos) e proximidades de um lugar. Distâncias são **em linha reta** (Haversine) e rotuladas assim — nunca se inventam rotas.

**Estrutura**

- **Classe `ConfiguracaoMapaService`**
  - `executar()`
- **Classe `LugaresNoMapaService`**
  - `executar()`
- **Classe `MapaViagemService`**
  - `__init__(autorizacao)`
  - `executar(viagem_id, usuario)`
- **Classe `ProximidadesLugarService`**
  - `__init__(servico_pontos)`
  - `executar(lugar_id, raio_km, tipos)`

**Usa:** `config.py`, `models/lugar.py`, `services/autorizacao_viagem_service.py`, `services/integracoes/pontos_interesse_service.py`, `utils/erros.py`, `utils/geo.py`  
**Usado por:** `controllers/mapa_controller.py`

### `backend/services/obter_lugar_service.py`  <small>(27 linhas)</small>

Detalhe de um lugar (match, distância, favorito). Na expansão inclui a lista de **fotos verificadas**.

**Estrutura**

- **Classe `ObterLugarService`**
  - `__init__(servico_match)`
  - `executar(lugar_id, usuario)`

**Usa:** `models/favorito.py`, `models/lugar.py`, `services/calcular_match_service.py`, `utils/erros.py`  
**Usado por:** `controllers/lugar_controller.py`

### `backend/services/obter_perfil_service.py`  <small>(14 linhas)</small>

Monta o perfil: dados do usuário, preferências, total de lugares salvos e se já tem preferências.

**Estrutura**

- **Classe `ObterPerfilService`**
  - `__init__(repositorio_favoritos)`
  - `executar(usuario)`

**Usa:** `repositories/favorito_repository.py`  
**Usado por:** `controllers/usuario_controller.py`

### `backend/services/recomendar_lugares_service.py`  <small>(54 linhas)</small>

Recomendações: pega candidatos das categorias de interesse e do orçamento (tolerando uma faixa acima), calcula o match de cada um e devolve os melhores.

**Estrutura**

- **Classe `RecomendarLugaresService`**
  - `__init__(repositorio, repositorio_favoritos, servico_match)`
  - `executar(usuario, limite, categoria)`

**Usa:** `repositories/favorito_repository.py`, `repositories/lugar_repository.py`, `services/calcular_match_service.py`, `utils/erros.py`  
**Usado por:** `controllers/lugar_controller.py`, `services/enviar_mensagem_chat_service.py`

### `backend/services/reenviar_codigo_service.py`  <small>(29 linhas)</small>

Invalida códigos antigos, emite um novo e o envia; recusa contas já verificadas.

**Estrutura**

- **Classe `ReenviarCodigoService`**
  - `__init__(servico_email)`
  - `executar(dados)`

**Usa:** `config.py`, `models/codigo_verificacao.py`, `models/usuario.py`, `services/envio_email_service.py`, `utils/erros.py`, `utils/validadores.py`  
**Usado por:** `controllers/auth_controller.py`

### `backend/services/remover_favorito_service.py`  <small>(13 linhas)</small>

Remove um favorito; 404 se o lugar não estava salvo.

**Estrutura**

- **Classe `RemoverFavoritoService`**
  - `executar(usuario, lugar_id)`

**Usa:** `models/favorito.py`, `utils/erros.py`  
**Usado por:** `controllers/favorito_controller.py`

### `backend/services/roteiro_inteligente_service.py`  <small>(369 linhas)</small>

Motor do roteiro. Passos: (1) **candidatos reais** — lugares do catálogo num raio de 80 km e pontos do OpenStreetMap num raio de 6 km; (2) **pontuação** por interesses, orçamento e nota (o destino escolhido ganha +10); (3) escolhe quantos cabem por dia conforme o ritmo; (4) ordena por **vizinho mais próximo** a partir do centro, para reduzir deslocamentos; (5) monta cada dia com almoço no meio e jantar no fim; (6) confere o `opening_hours` do OSM (ajusta o horário ou avisa que pode estar fechado). Dias sem opções viram "Tempo livre" — nunca se inventa lugar.
Com Gemini, a IA só devolve **chaves** de candidatos; qualquer chave desconhecida é descartada e, se nada sobrar, usa-se o motor local.

**Estrutura**

- **Constantes:** `RITMOS`, `RAIO_CATALOGO_KM`, `RAIO_PONTOS_KM`, `DURACAO_ESTIMADA`, `CATEGORIA_ATIVIDADE`, `DIAS_OSM`
- **Função `_normalizar(texto)`**
- **Função `interpretar_funcionamento(valor)`** — Interpreta formatos simples de opening_hours ("Tu-Su 10:00-18:00; Mo off").
- **Classe `RoteiroInteligenteService`**
  - `__init__(servico_pontos, servico_ia)`
  - `executar(viagem, parametros)`
  - `_ordenar_por_proximidade(itens, inicio)` — Vizinho mais próximo a partir do centro: reduz deslocamentos desnecessários.
  - `_conferir_funcionamento(viagem, plano)` — Ajusta/alerta com base no opening_hours do OSM (único dado de horário confiável).

**Usa:** `models/lugar.py`, `services/gemini_service.py`, `services/integracoes/pontos_interesse_service.py`, `utils/geo.py`, `utils/validadores.py`  
**Usado por:** `services/roteiros_service.py`, `tests/test_funcionalidades.py`

### `backend/services/roteiros_service.py`  <small>(285 linhas)</small>

Versões de roteiro e atividades. Limites: 20 versões e 300 atividades. `nova_versao_roteiro` desativa as outras e cria a nova como principal. `validar_atividade` valida dia (dentro da duração), horário HH:MM, duração, lugar do catálogo e coordenadas; digitar um horário remove a marca de "sugerido". `ReorganizarAtividadesService` aplica mover/reordenar em lote.

**Estrutura**

- **Constantes:** `MAXIMO_VERSOES`, `MAXIMO_ATIVIDADES`
- **Função `nova_versao_roteiro(viagem, usuario, titulo, origem, parametros, observacoes)`**
- **Função `_roteiro_autorizado(roteiro_id, usuario, autorizacao, nivel)`**
- **Função `_atividade_autorizada(atividade_id, usuario, autorizacao)`**
- **Função `validar_atividade(dados, viagem, atual)`**
- **Classe `GerarRoteiroService`**
  - `__init__(autorizacao, motor)`
  - `executar(viagem_id, usuario, dados)`
- **Classe `ListarRoteirosService`**
  - `__init__(autorizacao)`
  - `executar(viagem_id, usuario)`
- **Classe `ObterRoteiroService`**
  - `__init__(autorizacao)`
  - `executar(roteiro_id, usuario)`
- **Classe `CriarRoteiroManualService`**
  - `__init__(autorizacao)`
  - `executar(viagem_id, usuario, dados)`
- **Classe `DuplicarRoteiroService`**
  - `__init__(autorizacao)`
  - `executar(roteiro_id, usuario)`
- **Classe `AtivarRoteiroService`**
  - `__init__(autorizacao)`
  - `executar(roteiro_id, usuario)`
- **Classe `ExcluirRoteiroService`**
  - `__init__(autorizacao)`
  - `executar(roteiro_id, usuario)`
- **Classe `AdicionarAtividadeService`**
  - `__init__(autorizacao)`
  - `executar(roteiro_id, usuario, dados)`
- **Classe `EditarAtividadeService`**
  - `__init__(autorizacao)`
  - `executar(atividade_id, usuario, dados)`
- **Classe `ExcluirAtividadeService`**
  - `__init__(autorizacao)`
  - `executar(atividade_id, usuario)`
- **Classe `ReorganizarAtividadesService`** — Recebe [{id, dia, ordem}] e aplica em lote (mover entre dias e reordenar).
  - `__init__(autorizacao)`
  - `executar(roteiro_id, usuario, dados)`

**Usa:** `extensions.py`, `models/lugar.py`, `models/ponto_interesse.py`, `models/roteiro.py`, `services/autorizacao_viagem_service.py`, `services/roteiro_inteligente_service.py`, `utils/erros.py`, `utils/validadores.py`  
**Usado por:** `controllers/roteiro_controller.py`, `services/grupo_service.py`

### `backend/services/salvar_favorito_service.py`  <small>(21 linhas)</small>

Salva um lugar nos favoritos (idempotente: salvar duas vezes não duplica).

**Estrutura**

- **Classe `SalvarFavoritoService`**
  - `executar(usuario, lugar_id)`

**Usa:** `models/favorito.py`, `models/lugar.py`, `utils/erros.py`  
**Usado por:** `controllers/favorito_controller.py`

### `backend/services/salvar_preferencias_service.py`  <small>(40 linhas)</small>

Valida e grava interesses, orçamento, cidade e UF do usuário.

**Estrutura**

- **Classe `SalvarPreferenciasService`**
  - `executar(usuario, dados)`

**Usa:** `models/interesse.py`, `models/preferencia.py`, `utils/erros.py`, `utils/validadores.py`  
**Usado por:** `controllers/preferencia_controller.py`

### `backend/services/verificar_codigo_service.py`  <small>(33 linhas)</small>

Confere o código (não usado e não expirado), marca a conta como verificada e já devolve o token de sessão.

**Estrutura**

- **Classe `VerificarCodigoService`**
  - `executar(dados)`

**Usa:** `models/codigo_verificacao.py`, `models/usuario.py`, `utils/erros.py`, `utils/validadores.py`  
**Usado por:** `controllers/auth_controller.py`

### `backend/services/viagens_service.py`  <small>(164 linhas)</small>

CRUD do planejador. `_validar_dados_viagem` valida (datas coerentes, no máximo 90 dias, 1–50 viajantes, tipo, orçamento em centavos) e aceita edição parcial. As coordenadas vêm do lugar do catálogo, do clique no mapa ou da geocodificação (que, se falhar, deixa sem coordenadas). Excluir apaga tudo da viagem em cascata.

**Estrutura**

- **Constantes:** `DURACAO_MAXIMA_DIAS`
- **Função `_validar_dados_viagem(dados, atual)`** — Valida e normaliza os campos; `atual` permite edição parcial.
- **Função `_definir_coordenadas(viagem, dados, geocodificador, destino_mudou)`**
- **Classe `CriarViagemService`**
  - `__init__(geocodificador)`
  - `executar(usuario, dados)`
- **Classe `ListarViagensService`**
  - `__init__(repositorio)`
  - `executar(usuario, status)`
- **Classe `ObterViagemService`**
  - `__init__(autorizacao, repositorio)`
  - `executar(viagem_id, usuario)`
- **Classe `EditarViagemService`**
  - `__init__(autorizacao, geocodificador)`
  - `executar(viagem_id, usuario, dados)`
- **Classe `ExcluirViagemService`**
  - `__init__(autorizacao)`
  - `executar(viagem_id, usuario)`

**Usa:** `extensions.py`, `models/lugar.py`, `models/viagem.py`, `repositories/viagem_repository.py`, `services/autorizacao_viagem_service.py`, `services/integracoes/geocodificacao_service.py`, `utils/erros.py`, `utils/validadores.py`  
**Usado por:** `controllers/viagem_controller.py`

---

## 5. Backend — Integrações externas

### `backend/services/integracoes/__init__.py`  <small>(11 linhas)</small>

Docstring que lista as integrações externas e o papel de cada uma.

### `backend/services/integracoes/cliente_http.py`  <small>(87 linhas)</small>

Cliente HTTP único para todas as integrações: manda User-Agent identificado, espera o intervalo mínimo por site (Nominatim 1,1 s), usa **cache persistente** (`cache_externo`) e converte qualquer falha (rede, timeout, 429, JSON ruim) em `IntegracaoIndisponivel` — os Services tratam isso sem derrubar a tela. `INTEGRACOES_EXTERNAS=0` desliga tudo.

**Estrutura**

- **Constantes:** `INTERVALO_MINIMO`
- **Classe `ClienteHttp`**
  - `__init__(config, sessao)`
  - `habilitado()`
  - `requisitar_json(url, params, metodo, dados, cabecalhos, cache_horas, chave_cache)`

**Usa:** `config.py`, `models/cache_externo.py`, `utils/erros.py`  
**Usado por:** `services/integracoes/clima_service.py`, `services/integracoes/fotos_pexels_service.py`, `services/integracoes/fotos_unsplash_service.py`, `services/integracoes/fotos_wikimedia_service.py`, `services/integracoes/geocodificacao_service.py`, `services/integracoes/pontos_interesse_service.py`

### `backend/services/integracoes/clima_service.py`  <small>(49 linhas)</small>

Previsão de 7 dias no Open-Meteo (sem chave, cache de 6 h): médias de máxima/mínima e chance de chuva. Em qualquer falha devolve `None` — a interface mostra só a "melhor época" do catálogo, sem inventar clima.

**Estrutura**

- **Classe `ClimaService`**
  - `__init__(cliente, config)`
  - `executar(latitude, longitude)`

**Usa:** `config.py`, `services/integracoes/cliente_http.py`, `utils/erros.py`  
**Usado por:** `services/comparador_service.py`

### `backend/services/integracoes/fotos_pexels_service.py`  <small>(53 linhas)</small>

Busca no Pexels (exige `PEXELS_API_KEY`). Como busca por texto não garante que a foto é do lugar, tudo entra **não verificado** e só aparece depois de aprovado na curadoria.

**Estrutura**

- **Constantes:** `URL_BUSCA`
- **Classe `FotosPexelsService`**
  - `__init__(cliente, config)`
  - `configurado()`
  - `executar(lugar, referencia, limite)`

**Usa:** `config.py`, `services/integracoes/cliente_http.py`, `utils/erros.py`  
**Usado por:** `services/fotos_lugar_service.py`

### `backend/services/integracoes/fotos_unsplash_service.py`  <small>(68 linhas)</small>

Busca no Unsplash (exige `UNSPLASH_ACCESS_KEY`). Também entra como não verificada; cumpre as regras da API (créditos com `utm_source` e registro de download ao usar a foto).

**Estrutura**

- **Constantes:** `URL_API`, `UTM`
- **Classe `FotosUnsplashService`**
  - `__init__(cliente, config)`
  - `configurado()`
  - `executar(lugar, referencia, limite)`
  - `registrar_uso(id_externo)` — Endpoint de download exigido pelas diretrizes da API ao usar uma foto.

**Usa:** `config.py`, `services/integracoes/cliente_http.py`, `utils/erros.py`  
**Usado por:** `services/fotos_lugar_service.py`

### `backend/services/integracoes/fotos_wikimedia_service.py`  <small>(183 linhas)</small>

Fotos reais pela Wikipédia/Commons, sem chave. **Critérios de verificação:** (1) a imagem principal do artigo só é aceita se as coordenadas do artigo ficam dentro do raio do lugar (evita homônimos); (2) fotos georreferenciadas do Commons precisam estar no raio **e** ter o nome do lugar no título. Só licenças livres; guarda autor, licença e página de origem. `miniatura()` troca o `NNNpx-` da URL para obter tamanhos 480/1280/1920 px.

**Estrutura**

- **Constantes:** `LICENCAS_LIVRES`, `PALAVRAS_GENERICAS`, `LARGURA_MEDIA`, `LARGURA_MINIATURA`, `LARGURA_AMPLIADA`
- **Função `normalizar(texto)`**
- **Função `termos_do_lugar(nome, extras)`**
- **Função `limpar_html(valor)`**
- **Função `miniatura(url_thumb, largura)`** — Wikimedia gera miniaturas sob demanda trocando o prefixo 'NNNpx-' da URL.
- **Classe `FotosWikimediaService`**
  - `__init__(cliente, config)`
  - `executar(lugar, referencia, limite)` — Lista de candidatas (dicts) para o lugar. Lança IntegracaoIndisponivel se offline.

**Usa:** `config.py`, `services/integracoes/cliente_http.py`, `utils/erros.py`, `utils/geo.py`  
**Usado por:** `services/fotos_lugar_service.py`, `tests/test_funcionalidades.py`

### `backend/services/integracoes/geocodificacao_service.py`  <small>(42 linhas)</small>

Converte um destino digitado em latitude/longitude pelo Nominatim (cache de 30 dias). Se não achar ou estiver offline, devolve `None`.

**Estrutura**

- **Classe `GeocodificacaoService`**
  - `__init__(cliente, config)`
  - `executar(consulta)` — Devolve {latitude, longitude, nome, pais_codigo} ou None se não achar/indisponível.

**Usa:** `config.py`, `services/integracoes/cliente_http.py`, `utils/erros.py`  
**Usado por:** `services/viagens_service.py`

### `backend/services/integracoes/pontos_interesse_service.py`  <small>(139 linhas)</small>

Busca restaurantes, museus, mirantes, parques etc. reais no Overpass API (1 consulta por região por semana), classifica pelas tags do OSM e grava em `pontos_interesse`. `proximos` devolve os já conhecidos num raio, com distância.

**Estrutura**

- **Constantes:** `CLASSIFICACAO`, `TIPOS_ROTULO`, `TIPO_PARA_INTERESSE`
- **Função `classificar(tags)`**
- **Classe `PontosInteresseService`**
  - `__init__(cliente, config)`
  - `atualizar(latitude, longitude, raio)` — Busca no Overpass (no máximo 1x por semana por região) e grava os pontos.
  - `proximos(latitude, longitude, raio_km, tipos, limite, buscar_externo)` — Pontos já conhecidos perto da coordenada (atualiza pelo Overpass se possível).
  - `limpar_antigos(dias)`

**Usa:** `config.py`, `extensions.py`, `models/cache_externo.py`, `models/ponto_interesse.py`, `services/integracoes/cliente_http.py`, `utils/datas.py`, `utils/erros.py`, `utils/geo.py`  
**Usado por:** `services/comparador_service.py`, `services/mapa_service.py`, `services/roteiro_inteligente_service.py`

---

## 6. Backend — Models (tabelas)

### `backend/models/__init__.py`  <small>(32 linhas)</small>

Importa todos os Models — necessário para o SQLAlchemy conhecer as tabelas e para `create_all` criá-las — e reexporta as constantes (tipos de viagem, categorias etc.).

**Usa:** `models/avaliacao.py`, `models/cache_externo.py`, `models/checklist.py`, `models/codigo_verificacao.py`, `models/compromisso.py`, `models/despesa.py`, `models/diario.py`, `models/favorito.py`, `models/foto_lugar.py`, `models/interesse.py`, `models/lugar.py`, `models/mensagem_chat.py` e mais 8  
**Usado por:** —

### `backend/models/avaliacao.py`  <small>(74 linhas)</small>

`Avaliacao` (restrições: **única por usuário e lugar** e nota entre 1 e 5; guarda `experiencia_verificada`) e `FotoAvaliacao` (só o nome do arquivo; a URL é assinada na hora).

**Tabela `avaliacoes`** (classe `Avaliacao`)

| Coluna | Tipo | Detalhes |
|---|---|---|
| `id` | `Integer` | chave primária |
| `usuario_id` | `Integer` | → `usuarios.id`; obrigatório |
| `lugar_id` | `Integer` | → `lugares.id` (ON DELETE CASCADE); obrigatório |
| `nota` | `Integer` | obrigatório |
| `titulo` | `String(120)` |  |
| `comentario` | `Text` | obrigatório |
| `data_visita` | `Date` |  |
| `experiencia_verificada` | `Boolean` | obrigatório |
| `viagem_id` | `Integer` | → `viagens.id` (ON DELETE SET NULL) |
| `criado_em` | `DateTime` | obrigatório |
| `atualizado_em` | `DateTime` |  |

Relações:
- `usuario` → **Usuario**
- `lugar` → **Lugar**
- `fotos` → **FotoAvaliacao**

Restrições:
- db.UniqueConstraint("usuario_id", "lugar_id", name="uq_avaliacao_usuario_lugar")
- db.CheckConstraint("nota >= 1 AND nota <= 5", name="ck_avaliacao_nota")

**Tabela `fotos_avaliacao`** (classe `FotoAvaliacao`)

| Coluna | Tipo | Detalhes |
|---|---|---|
| `id` | `Integer` | chave primária |
| `avaliacao_id` | `Integer` | → `avaliacoes.id` (ON DELETE CASCADE); obrigatório |
| `arquivo` | `String(60)` | obrigatório |
| `criado_em` | `DateTime` | obrigatório |

Relações:
- `avaliacao` → **Avaliacao**

**Estrutura**

- **Classe `Avaliacao`** (db.Model, ModeloBase)
  - `buscar(cls, usuario_id, lugar_id)`
  - `to_dict(usuario_id, com_lugar)`
- **Classe `FotoAvaliacao`** (db.Model, ModeloBase)
  - `to_dict()`

**Usa:** `extensions.py`, `models/base.py`, `utils/arquivos.py`, `utils/datas.py`  
**Usado por:** `services/avaliacoes_service.py`, `services/comparador_service.py`, `tests/test_funcionalidades.py`

### `backend/models/base.py`  <small>(37 linhas)</small>

Mixin `ModeloBase` herdado por todos os Models: `salvar`, `atualizar`, `deletar`, `listar_todos`, `buscar_por_id` e `contar`. É o "CRUD convencional" que fica na própria entidade.

**Estrutura**

- **Classe `ModeloBase`** — Mixin com o CRUD convencional herdado por todas as Models.
  - `salvar()`
  - `atualizar(**campos)`
  - `deletar()`
  - `listar_todos(cls)`
  - `buscar_por_id(cls, identificador)`
  - `contar(cls)`

**Usa:** `extensions.py`  
**Usado por:** `models/avaliacao.py`, `models/cache_externo.py`, `models/checklist.py`, `models/codigo_verificacao.py`, `models/compromisso.py`, `models/despesa.py`, `models/diario.py`, `models/favorito.py`, `models/foto_lugar.py`, `models/interesse.py`, `models/lugar.py`, `models/mensagem_chat.py` e mais 7

### `backend/models/cache_externo.py`  <small>(35 linhas)</small>

Cache chave→JSON com expiração para respostas de integrações (`ler`/`gravar`).

**Tabela `cache_externo`** (classe `CacheExterno`)

| Coluna | Tipo | Detalhes |
|---|---|---|
| `id` | `Integer` | chave primária |
| `chave` | `String(255)` | único; obrigatório |
| `conteudo` | `Text` | obrigatório |
| `expira_em` | `DateTime` | obrigatório |

**Estrutura**

- **Classe `CacheExterno`** (db.Model, ModeloBase)
  - `ler(cls, chave)`
  - `gravar(cls, chave, valor, horas)`

**Usa:** `extensions.py`, `models/base.py`, `utils/datas.py`  
**Usado por:** `services/integracoes/cliente_http.py`, `services/integracoes/pontos_interesse_service.py`

### `backend/models/checklist.py`  <small>(43 linhas)</small>

`ItemChecklist` (texto, categoria, concluído, se veio de sugestão, ordem).

**Tabela `itens_checklist`** (classe `ItemChecklist`)

| Coluna | Tipo | Detalhes |
|---|---|---|
| `id` | `Integer` | chave primária |
| `viagem_id` | `Integer` | → `viagens.id` (ON DELETE CASCADE); obrigatório |
| `categoria` | `String(20)` | obrigatório |
| `texto` | `String(160)` | obrigatório |
| `concluido` | `Boolean` | obrigatório |
| `sugerido` | `Boolean` | obrigatório |
| `ordem` | `Integer` | obrigatório |
| `atualizado_por_id` | `Integer` | → `usuarios.id` |
| `criado_em` | `DateTime` | obrigatório |
| `atualizado_em` | `DateTime` |  |

Relações:
- `viagem` → **Viagem**

**Estrutura**

- **Constantes:** `CATEGORIAS_CHECKLIST`
- **Classe `ItemChecklist`** (db.Model, ModeloBase)
  - `to_dict()`

**Usa:** `extensions.py`, `models/base.py`, `utils/datas.py`  
**Usado por:** `repositories/viagem_repository.py`, `services/checklist_service.py`

### `backend/models/codigo_verificacao.py`  <small>(69 linhas)</small>

Código de 6 dígitos com validade. `emitir_para` invalida os anteriores antes de criar o novo; `buscar_valido` só devolve códigos não usados e não expirados.

**Tabela `codigos_verificacao`** (classe `CodigoVerificacao`)

| Coluna | Tipo | Detalhes |
|---|---|---|
| `id` | `Integer` | chave primária |
| `usuario_id` | `Integer` | → `usuarios.id`; obrigatório |
| `codigo` | `String(6)` | obrigatório |
| `expira_em` | `DateTime` | obrigatório |
| `usado` | `Boolean` | obrigatório |
| `criado_em` | `DateTime` | obrigatório |

Relações:
- `usuario` → **Usuario**

**Estrutura**

- **Classe `CodigoVerificacao`** (db.Model, ModeloBase)
  - `gerar_codigo()`
  - `emitir_para(cls, usuario)` — Invalida códigos anteriores e cria um novo.
  - `listar_por_usuario(cls, usuario_id)`
  - `buscar_valido(cls, usuario_id, codigo)`
  - `marcar_como_usado()`
  - `expirado()`

**Usa:** `config.py`, `extensions.py`, `models/base.py`, `utils/datas.py`  
**Usado por:** `services/cadastrar_usuario_service.py`, `services/reenviar_codigo_service.py`, `services/verificar_codigo_service.py`

### `backend/models/compromisso.py`  <small>(56 linhas)</small>

`Compromisso` da agenda (início, duração, tipo, local, coordenadas). A propriedade `fim` é calculada.

**Tabela `compromissos`** (classe `Compromisso`)

| Coluna | Tipo | Detalhes |
|---|---|---|
| `id` | `Integer` | chave primária |
| `viagem_id` | `Integer` | → `viagens.id` (ON DELETE CASCADE); obrigatório |
| `titulo` | `String(160)` | obrigatório |
| `tipo` | `String(20)` | obrigatório |
| `inicio` | `DateTime` | obrigatório |
| `duracao_min` | `Integer` | obrigatório |
| `local` | `String(200)` |  |
| `latitude` | `Float` |  |
| `longitude` | `Float` |  |
| `observacoes` | `Text` |  |
| `criado_por_id` | `Integer` | → `usuarios.id` |
| `criado_em` | `DateTime` | obrigatório |

Relações:
- `viagem` → **Viagem**

**Estrutura**

- **Constantes:** `TIPOS_COMPROMISSO`
- **Classe `Compromisso`** (db.Model, ModeloBase)
  - `fim()`
  - `to_dict()`

**Usa:** `extensions.py`, `models/base.py`, `utils/datas.py`  
**Usado por:** `repositories/viagem_repository.py`, `services/calendario_service.py`

### `backend/models/despesa.py`  <small>(60 linhas)</small>

`Despesa` (valor em centavos ≥ 0, categoria, data, quem pagou) e `PlanejamentoOrcamento` (valor planejado por categoria). Define as categorias com ícone e cor.

**Tabela `despesas`** (classe `Despesa`)

| Coluna | Tipo | Detalhes |
|---|---|---|
| `id` | `Integer` | chave primária |
| `viagem_id` | `Integer` | → `viagens.id` (ON DELETE CASCADE); obrigatório |
| `descricao` | `String(160)` | obrigatório |
| `categoria` | `String(20)` | obrigatório |
| `valor_centavos` | `Integer` | obrigatório |
| `data` | `Date` |  |
| `pago_por_id` | `Integer` | → `usuarios.id` |
| `criado_por_id` | `Integer` | → `usuarios.id`; obrigatório |
| `criado_em` | `DateTime` | obrigatório |

Relações:
- `viagem` → **Viagem**
- `pago_por` → **Usuario**
- `criado_por` → **Usuario**

Restrições:
- db.CheckConstraint("valor_centavos >= 0", name="ck_despesa_valor"),)

**Tabela `planejamento_orcamento`** (classe `PlanejamentoOrcamento`)

| Coluna | Tipo | Detalhes |
|---|---|---|
| `id` | `Integer` | chave primária |
| `viagem_id` | `Integer` | → `viagens.id` (ON DELETE CASCADE); obrigatório |
| `categoria` | `String(20)` | obrigatório |
| `valor_centavos` | `Integer` | obrigatório |

Relações:
- `viagem` → **Viagem**

Restrições:
- db.UniqueConstraint("viagem_id", "categoria", name="uq_planejamento_categoria"),)

**Estrutura**

- **Constantes:** `CATEGORIAS_DESPESA`
- **Classe `Despesa`** (db.Model, ModeloBase)
  - `to_dict()`
- **Classe `PlanejamentoOrcamento`** (db.Model, ModeloBase) — Valor planejado por categoria (opcional, complementa o orçamento total).

**Usa:** `extensions.py`, `models/base.py`, `utils/datas.py`  
**Usado por:** `repositories/viagem_repository.py`, `services/financas_service.py`

### `backend/models/diario.py`  <small>(72 linhas)</small>

`RegistroDiario` (relato, data, local, nota pessoal 1–5, visibilidade) e `FotoDiario`.

**Tabela `registros_diario`** (classe `RegistroDiario`)

| Coluna | Tipo | Detalhes |
|---|---|---|
| `id` | `Integer` | chave primária |
| `usuario_id` | `Integer` | → `usuarios.id`; obrigatório |
| `viagem_id` | `Integer` | → `viagens.id` (ON DELETE SET NULL) |
| `lugar_id` | `Integer` | → `lugares.id` (ON DELETE SET NULL) |
| `titulo` | `String(140)` | obrigatório |
| `relato` | `Text` |  |
| `data` | `Date` | obrigatório |
| `local` | `String(160)` |  |
| `cidade` | `String(80)` |  |
| `estado` | `String(60)` |  |
| `nota_pessoal` | `Integer` |  |
| `visibilidade` | `String(14)` | obrigatório |
| `criado_em` | `DateTime` | obrigatório |
| `atualizado_em` | `DateTime` |  |

Relações:
- `usuario` → **Usuario**
- `viagem` → **Viagem**
- `lugar` → **Lugar**
- `fotos` → **FotoDiario**

Restrições:
- db.CheckConstraint("nota_pessoal IS NULL OR (nota_pessoal >= 1 AND nota_pessoal <= 5)

**Tabela `fotos_diario`** (classe `FotoDiario`)

| Coluna | Tipo | Detalhes |
|---|---|---|
| `id` | `Integer` | chave primária |
| `registro_id` | `Integer` | → `registros_diario.id` (ON DELETE CASCADE); obrigatório |
| `arquivo` | `String(60)` | obrigatório |
| `legenda` | `String(160)` |  |
| `criado_em` | `DateTime` | obrigatório |

Relações:
- `registro` → **RegistroDiario**

**Estrutura**

- **Constantes:** `VISIBILIDADES`
- **Classe `RegistroDiario`** (db.Model, ModeloBase)
  - `to_dict(usuario_id)`
- **Classe `FotoDiario`** (db.Model, ModeloBase)
  - `to_dict()`

**Usa:** `extensions.py`, `models/base.py`, `utils/arquivos.py`, `utils/datas.py`  
**Usado por:** `services/assistente_service.py`, `services/avaliacoes_service.py`, `services/diario_service.py`

### `backend/models/favorito.py`  <small>(34 linhas)</small>

Lugar salvo por um usuário; restrição única (usuário, lugar).

**Tabela `favoritos`** (classe `Favorito`)

| Coluna | Tipo | Detalhes |
|---|---|---|
| `id` | `Integer` | chave primária |
| `usuario_id` | `Integer` | → `usuarios.id`; obrigatório |
| `lugar_id` | `Integer` | → `lugares.id`; obrigatório |
| `criado_em` | `DateTime` | obrigatório |

Relações:
- `usuario` → **Usuario**
- `lugar` → **Lugar**

Restrições:
- db.UniqueConstraint("usuario_id", "lugar_id", name="uq_favorito_usuario_lugar"),)

**Estrutura**

- **Classe `Favorito`** (db.Model, ModeloBase)
  - `buscar(cls, usuario_id, lugar_id)`
  - `to_dict()`

**Usa:** `extensions.py`, `models/base.py`, `utils/datas.py`  
**Usado por:** `repositories/favorito_repository.py`, `services/obter_lugar_service.py`, `services/remover_favorito_service.py`, `services/salvar_favorito_service.py`

### `backend/models/foto_lugar.py`  <small>(72 linhas)</small>

`FotoLugar`: fonte, URLs (original, ampliada, média, miniatura), dimensões, **autor, licença e página de origem**, critério de verificação, `verificada` e `principal`. Só fotos verificadas chegam ao usuário.

**Tabela `fotos_lugar`** (classe `FotoLugar`)

| Coluna | Tipo | Detalhes |
|---|---|---|
| `id` | `Integer` | chave primária |
| `lugar_id` | `Integer` | → `lugares.id` (ON DELETE CASCADE); obrigatório |
| `fonte` | `String(20)` | obrigatório |
| `id_externo` | `String(200)` |  |
| `url` | `String(600)` | obrigatório |
| `url_media` | `String(600)` |  |
| `url_miniatura` | `String(600)` |  |
| `url_original` | `String(600)` |  |
| `largura` | `Integer` |  |
| `altura` | `Integer` |  |
| `titulo` | `String(300)` |  |
| `autor` | `String(200)` |  |
| `autor_url` | `String(400)` |  |
| `licenca` | `String(80)` |  |
| `licenca_url` | `String(400)` |  |
| `pagina_origem` | `String(600)` |  |
| `criterio_verificacao` | `String(200)` |  |
| `verificada` | `Boolean` | obrigatório |
| `principal` | `Boolean` | obrigatório |
| `ordem` | `Integer` | obrigatório |
| `criado_em` | `DateTime` | obrigatório |

Relações:
- `lugar` → **Lugar**

Restrições:
- db.UniqueConstraint("lugar_id", "url", name="uq_foto_lugar_url"),)

**Estrutura**

- **Constantes:** `FONTES_FOTO`
- **Classe `FotoLugar`** (db.Model, ModeloBase)
  - `to_dict(completo)`

**Usa:** `extensions.py`, `models/base.py`, `utils/datas.py`  
**Usado por:** `services/fotos_lugar_service.py`, `tests/test_funcionalidades.py`, `tools/fotos.py`

### `backend/models/interesse.py`  <small>(34 linhas)</small>

Catálogo de interesses (slug, nome, ícone, cor) e a tabela associativa N:N com `preferencias`.

**Tabela `interesses`** (classe `Interesse`)

| Coluna | Tipo | Detalhes |
|---|---|---|
| `id` | `Integer` | chave primária |
| `slug` | `String(40)` | único; obrigatório |
| `nome` | `String(60)` | obrigatório |
| `icone` | `String(10)` | obrigatório |
| `cor` | `String(20)` | obrigatório |

**Estrutura**

- **Classe `Interesse`** (db.Model, ModeloBase)
  - `buscar_por_slug(cls, slug)`
  - `buscar_por_slugs(cls, slugs)`
  - `to_dict()`

**Usa:** `extensions.py`, `models/base.py`  
**Usado por:** `models/preferencia.py`, `seeds.py`, `services/comparador_service.py`, `services/listar_interesses_service.py`, `services/salvar_preferencias_service.py`

### `backend/models/lugar.py`  <small>(84 linhas)</small>

Destino, restaurante ou experiência do catálogo. Na expansão ganhou `fotos` (carregadas em lote para evitar N+1), `tipo` (estabelecimento × atração), `fotos_verificadas` e `foto_principal_dict`. O `to_dict` agora inclui `foto`, `total_fotos`, `tipo`, latitude e longitude.

**Tabela `lugares`** (classe `Lugar`)

| Coluna | Tipo | Detalhes |
|---|---|---|
| `id` | `Integer` | chave primária |
| `nome` | `String(120)` | obrigatório |
| `categoria` | `String(40)` | obrigatório; slug do Interesse |
| `cidade` | `String(80)` | obrigatório |
| `estado` | `String(2)` | obrigatório |
| `descricao` | `Text` | obrigatório |
| `nota` | `Float` | obrigatório |
| `avaliacoes` | `Integer` | obrigatório |
| `faixa_preco` | `Integer` | obrigatório; 1 a 4 |
| `imagem` | `String(120)` | obrigatório |
| `latitude` | `Float` | obrigatório |
| `longitude` | `Float` | obrigatório |
| `melhor_epoca` | `String(80)` |  |
| `criado_em` | `DateTime` | obrigatório |

Relações:
- `favoritos` → **Favorito**
- `fotos` → **FotoLugar**

**Estrutura**

- **Classe `Lugar`** (db.Model, ModeloBase)
  - `listar_por_categoria(cls, categoria)`
  - `tipo()` — Natureza do lugar: estabelecimento (restaurantes/mercados) ou atração/destino.
  - `fotos_verificadas()`
  - `foto_principal_dict()`
  - `preco_simbolo()`
  - `to_dict(match, distancia_km, favorito)`

**Usa:** `extensions.py`, `models/base.py`, `utils/datas.py`  
**Usado por:** `repositories/lugar_repository.py`, `seeds.py`, `services/assistente_service.py`, `services/avaliacoes_service.py`, `services/comparador_service.py`, `services/diario_service.py`, `services/fotos_lugar_service.py`, `services/grupo_service.py`, `services/mapa_service.py`, `services/obter_lugar_service.py`, `services/roteiro_inteligente_service.py`, `services/roteiros_service.py` e mais 4

### `backend/models/mensagem_chat.py`  <small>(36 linhas)</small>

Mensagens da conversa com o Vai (autor `usuario` ou `ia`).

**Tabela `mensagens_chat`** (classe `MensagemChat`)

| Coluna | Tipo | Detalhes |
|---|---|---|
| `id` | `Integer` | chave primária |
| `usuario_id` | `Integer` | → `usuarios.id`; obrigatório |
| `autor` | `String(10)` | obrigatório; "usuario" ou "ia" |
| `texto` | `Text` | obrigatório |
| `criado_em` | `DateTime` | obrigatório |

Relações:
- `usuario` → **Usuario**

**Estrutura**

- **Classe `MensagemChat`** (db.Model, ModeloBase)
  - `listar_por_usuario(cls, usuario_id, limite)`
  - `to_dict()`

**Usa:** `extensions.py`, `models/base.py`, `utils/datas.py`  
**Usado por:** `services/enviar_mensagem_chat_service.py`, `services/listar_historico_chat_service.py`

### `backend/models/migracao.py`  <small>(12 linhas)</small>

Tabela `migracoes_aplicadas` (nome único + data), usada por `migracoes.py`.

**Tabela `migracoes_aplicadas`** (classe `MigracaoAplicada`)

| Coluna | Tipo | Detalhes |
|---|---|---|
| `id` | `Integer` | chave primária |
| `nome` | `String(120)` | único; obrigatório |
| `aplicada_em` | `DateTime` | obrigatório |

**Estrutura**

- **Classe `MigracaoAplicada`** (db.Model)

**Usa:** `extensions.py`, `utils/datas.py`  
**Usado por:** `migracoes.py`

### `backend/models/permissao_assistente.py`  <small>(40 linhas)</small>

Consentimentos do Vai por usuário (favoritos, viagens, finanças, diário), todos `False` por padrão.

**Tabela `permissoes_assistente`** (classe `PermissaoAssistente`)

| Coluna | Tipo | Detalhes |
|---|---|---|
| `id` | `Integer` | chave primária |
| `usuario_id` | `Integer` | → `usuarios.id`; único; obrigatório |
| `usar_favoritos` | `Boolean` | obrigatório |
| `usar_viagens` | `Boolean` | obrigatório |
| `usar_financas` | `Boolean` | obrigatório |
| `usar_diario` | `Boolean` | obrigatório |
| `atualizado_em` | `DateTime` |  |

**Estrutura**

- **Constantes:** `ESCOPOS_ASSISTENTE`
- **Classe `PermissaoAssistente`** (db.Model, ModeloBase)
  - `do_usuario(cls, usuario_id)`
  - `to_dict()`

**Usa:** `extensions.py`, `models/base.py`, `utils/datas.py`  
**Usado por:** `services/assistente_service.py`

### `backend/models/ponto_interesse.py`  <small>(53 linhas)</small>

Cache persistente de estabelecimentos/atrações do OpenStreetMap (tipo OSM + id únicos, endereço, `opening_hours`, site).

**Tabela `pontos_interesse`** (classe `PontoInteresse`)

| Coluna | Tipo | Detalhes |
|---|---|---|
| `id` | `Integer` | chave primária |
| `osm_tipo` | `String(10)` | obrigatório; node | way | relation |
| `osm_id` | `BigInteger` | obrigatório |
| `nome` | `String(200)` | obrigatório |
| `tipo` | `String(30)` | obrigatório; restaurante, museu, atracao... |
| `latitude` | `Float` | obrigatório |
| `longitude` | `Float` | obrigatório |
| `endereco` | `String(240)` |  |
| `funcionamento` | `String(200)` |  |
| `site` | `String(300)` |  |
| `tags` | `Text` |  |
| `atualizado_em` | `DateTime` | obrigatório |

Restrições:
- db.UniqueConstraint("osm_tipo", "osm_id", name="uq_ponto_osm"),)

**Estrutura**

- **Classe `PontoInteresse`** (db.Model, ModeloBase)
  - `to_dict(distancia_km)`
  - `tags_dict()`

**Usa:** `extensions.py`, `models/base.py`, `utils/datas.py`  
**Usado por:** `services/integracoes/pontos_interesse_service.py`, `services/roteiros_service.py`, `tests/test_funcionalidades.py`

### `backend/models/preferencia.py`  <small>(55 linhas)</small>

Preferências do usuário (orçamento 1–4, cidade, UF e interesses). Define também `FAIXAS_ORCAMENTO` ($ a $$$$).

**Tabela `preferencias`** (classe `Preferencia`)

| Coluna | Tipo | Detalhes |
|---|---|---|
| `id` | `Integer` | chave primária |
| `orcamento` | `Integer` | obrigatório |
| `cidade` | `String(80)` |  |
| `estado` | `String(2)` |  |
| `atualizado_em` | `DateTime` |  |

Relações:
- `usuario` → **Usuario**
- `interesses` → **Interesse**

**Estrutura**

- **Constantes:** `FAIXAS_ORCAMENTO`
- **Classe `Preferencia`** (db.Model, ModeloBase)
  - `buscar_por_usuario(cls, usuario_id)`
  - `definir_interesses(interesses)`
  - `slugs_interesses()`
  - `to_dict()`

**Usa:** `extensions.py`, `models/base.py`, `models/interesse.py`, `utils/datas.py`  
**Usado por:** `services/enviar_mensagem_chat_service.py`, `services/listar_interesses_service.py`, `services/salvar_preferencias_service.py`

### `backend/models/roteiro.py`  <small>(120 linhas)</small>

`Roteiro` (uma **versão** por viagem, com `ativo` e os parâmetros usados) e `AtividadeRoteiro` (dia, ordem, horário, duração, lugar, coordenadas, fonte). Restrição única (viagem, versão).

**Tabela `roteiros`** (classe `Roteiro`)

| Coluna | Tipo | Detalhes |
|---|---|---|
| `id` | `Integer` | chave primária |
| `viagem_id` | `Integer` | → `viagens.id` (ON DELETE CASCADE); obrigatório |
| `versao` | `Integer` | obrigatório |
| `titulo` | `String(120)` | obrigatório |
| `origem` | `String(12)` | obrigatório; manual | local | gemini | copia |
| `ativo` | `Boolean` | obrigatório |
| `parametros` | `Text` | JSON com interesses, ritmo, orçamento... |
| `observacoes_ia` | `Text` |  |
| `criado_por_id` | `Integer` | → `usuarios.id` |
| `criado_em` | `DateTime` | obrigatório |

Relações:
- `viagem` → **Viagem**
- `criado_por` → **Usuario**
- `atividades` → **AtividadeRoteiro**

Restrições:
- db.UniqueConstraint("viagem_id", "versao", name="uq_roteiro_versao"),)

**Tabela `atividades_roteiro`** (classe `AtividadeRoteiro`)

| Coluna | Tipo | Detalhes |
|---|---|---|
| `id` | `Integer` | chave primária |
| `roteiro_id` | `Integer` | → `roteiros.id` (ON DELETE CASCADE); obrigatório |
| `dia` | `Integer` | obrigatório |
| `ordem` | `Integer` | obrigatório |
| `titulo` | `String(160)` | obrigatório |
| `descricao` | `Text` |  |
| `categoria` | `String(20)` | obrigatório |
| `horario` | `String(5)` | HH:MM |
| `horario_sugerido` | `Boolean` | obrigatório |
| `duracao_min` | `Integer` |  |
| `lugar_id` | `Integer` | → `lugares.id` (ON DELETE SET NULL) |
| `ponto_id` | `Integer` | → `pontos_interesse.id` (ON DELETE SET NULL) |
| `endereco` | `String(200)` |  |
| `latitude` | `Float` |  |
| `longitude` | `Float` |  |
| `funcionamento` | `String(200)` |  |
| `fonte` | `String(30)` | catalogo | openstreetmap | manual | sugestao |
| `criado_em` | `DateTime` | obrigatório |

Relações:
- `roteiro` → **Roteiro**
- `lugar` → **Lugar**
- `ponto` → **PontoInteresse**

**Estrutura**

- **Constantes:** `CATEGORIAS_ATIVIDADE`
- **Classe `Roteiro`** (db.Model, ModeloBase)
  - `proxima_versao(cls, viagem_id)`
  - `to_dict(com_atividades)`
- **Classe `AtividadeRoteiro`** (db.Model, ModeloBase)
  - `to_dict()`

**Usa:** `extensions.py`, `models/base.py`, `utils/datas.py`  
**Usado por:** `repositories/viagem_repository.py`, `services/grupo_service.py`, `services/roteiros_service.py`

### `backend/models/sugestao.py`  <small>(61 linhas)</small>

`SugestaoViagem` (aberta/aprovada/rejeitada, ligada à atividade criada) e `VotoSugestao` (+1/−1, único por usuário).

**Tabela `sugestoes_viagem`** (classe `SugestaoViagem`)

| Coluna | Tipo | Detalhes |
|---|---|---|
| `id` | `Integer` | chave primária |
| `viagem_id` | `Integer` | → `viagens.id` (ON DELETE CASCADE); obrigatório |
| `autor_id` | `Integer` | → `usuarios.id`; obrigatório |
| `titulo` | `String(160)` | obrigatório |
| `descricao` | `Text` |  |
| `lugar_id` | `Integer` | → `lugares.id` (ON DELETE SET NULL) |
| `status` | `String(10)` | obrigatório; aberta | aprovada | rejeitada |
| `decidido_por_id` | `Integer` | → `usuarios.id` |
| `atividade_id` | `Integer` | → `atividades_roteiro.id` (ON DELETE SET NULL) |
| `criado_em` | `DateTime` | obrigatório |
| `decidido_em` | `DateTime` |  |

Relações:
- `viagem` → **Viagem**
- `autor` → **Usuario**
- `decidido_por` → **Usuario**
- `lugar` → **Lugar**
- `votos` → **VotoSugestao**

**Tabela `votos_sugestao`** (classe `VotoSugestao`)

| Coluna | Tipo | Detalhes |
|---|---|---|
| `id` | `Integer` | chave primária |
| `usuario_id` | `Integer` | → `usuarios.id`; obrigatório |
| `valor` | `Integer` | obrigatório; +1 ou -1 |

Relações:
- `sugestao` → **SugestaoViagem**

Restrições:
- db.UniqueConstraint("sugestao_id", "usuario_id", name="uq_voto_usuario"),)

**Estrutura**

- **Classe `SugestaoViagem`** (db.Model, ModeloBase)
  - `to_dict(usuario_id)`
- **Classe `VotoSugestao`** (db.Model, ModeloBase)

**Usa:** `extensions.py`, `models/base.py`, `utils/datas.py`  
**Usado por:** `services/grupo_service.py`

### `backend/models/usuario.py`  <small>(78 linhas)</small>

Conta do usuário: nome, e-mail único, hash da senha, verificado, token de sessão. Tem relações com preferência, favoritos, códigos e mensagens (todas em cascata). `iniciais` e `primeiro_nome` alimentam a interface.

**Tabela `usuarios`** (classe `Usuario`)

| Coluna | Tipo | Detalhes |
|---|---|---|
| `id` | `Integer` | chave primária |
| `nome` | `String(120)` | obrigatório |
| `email` | `String(120)` | único; obrigatório |
| `senha_hash` | `String(255)` | obrigatório |
| `verificado` | `Boolean` | obrigatório |
| `token` | `String(64)` | único |
| `criado_em` | `DateTime` | obrigatório |

Relações:
- `preferencia` → **Preferencia**
- `favoritos` → **Favorito**
- `codigos` → **CodigoVerificacao**
- `mensagens` → **MensagemChat**

**Estrutura**

- **Classe `Usuario`** (db.Model, ModeloBase)
  - `definir_senha(senha_pura)`
  - `conferir_senha(senha_pura)`
  - `gerar_token()`
  - `iniciais()`
  - `primeiro_nome()`
  - `buscar_por_email(cls, email)`
  - `buscar_por_token(cls, token)`
  - `to_dict(incluir_preferencias)`

**Usa:** `extensions.py`, `models/base.py`, `utils/datas.py`  
**Usado por:** `services/autenticar_usuario_service.py`, `services/cadastrar_usuario_service.py`, `services/grupo_service.py`, `services/reenviar_codigo_service.py`, `services/verificar_codigo_service.py`, `utils/autenticacao.py`

### `backend/models/viagem.py`  <small>(201 linhas)</small>

`Viagem` (dono, destino, coordenadas, datas, viajantes, tipo, orçamento em centavos, observações) e `ParticipanteViagem` (papel e status do convite). A regra de **status** (futura/em andamento/concluída) e `papel_de(usuario)` ficam aqui. Há `CheckConstraint` garantindo retorno ≥ ida.

**Tabela `viagens`** (classe `Viagem`)

| Coluna | Tipo | Detalhes |
|---|---|---|
| `id` | `Integer` | chave primária |
| `proprietario_id` | `Integer` | → `usuarios.id`; obrigatório |
| `lugar_id` | `Integer` | → `lugares.id` (ON DELETE SET NULL) |
| `titulo` | `String(120)` | obrigatório |
| `destino` | `String(160)` | obrigatório |
| `latitude` | `Float` |  |
| `longitude` | `Float` |  |
| `data_ida` | `Date` | obrigatório |
| `data_volta` | `Date` | obrigatório |
| `viajantes` | `Integer` | obrigatório |
| `tipo` | `String(20)` | obrigatório |
| `orcamento_centavos` | `Integer` |  |
| `observacoes` | `Text` |  |
| `preferencias` | `Text` |  |
| `criado_em` | `DateTime` | obrigatório |
| `atualizado_em` | `DateTime` |  |

Relações:
- `proprietario` → **Usuario**
- `lugar` → **Lugar**
- `participantes` → **ParticipanteViagem**
- `roteiros` → **Roteiro**
- `despesas` → **Despesa**
- `planejamento` → **PlanejamentoOrcamento**
- `itens_checklist` → **ItemChecklist**
- `compromissos` → **Compromisso**
- `sugestoes` → **SugestaoViagem**

Restrições:
- db.CheckConstraint("data_volta >= data_ida", name="ck_viagem_datas"),)

**Tabela `participantes_viagem`** (classe `ParticipanteViagem`)

| Coluna | Tipo | Detalhes |
|---|---|---|
| `id` | `Integer` | chave primária |
| `viagem_id` | `Integer` | → `viagens.id` (ON DELETE CASCADE); obrigatório |
| `usuario_id` | `Integer` | → `usuarios.id`; obrigatório |
| `convidado_por_id` | `Integer` | → `usuarios.id` |
| `papel` | `String(12)` | obrigatório |
| `status` | `String(10)` | obrigatório; pendente | aceito | recusado |
| `criado_em` | `DateTime` | obrigatório |
| `respondido_em` | `DateTime` |  |

Relações:
- `viagem` → **Viagem**
- `usuario` → **Usuario**
- `convidado_por` → **Usuario**

Restrições:
- db.UniqueConstraint("viagem_id", "usuario_id", name="uq_participante_viagem"),)

**Estrutura**

- **Constantes:** `TIPOS_VIAGEM`, `PAPEIS`
- **Classe `Viagem`** (db.Model, ModeloBase)
  - `duracao_dias()`
  - `status_em(referencia)`
  - `status()`
  - `data_do_dia(numero_dia)`
  - `participante(usuario_id)`
  - `papel_de(usuario_id)` — 'proprietario', 'editor', 'viajante', 'convidado' (pendente) ou None.
  - `membros_ids()`
  - `roteiro_ativo()`
  - `to_dict(usuario_id, resumo)`
- **Classe `ParticipanteViagem`** (db.Model, ModeloBase)
  - `convites_pendentes(cls, usuario_id)`
  - `to_dict()`
  - `to_convite_dict()`

**Usa:** `extensions.py`, `models/base.py`, `utils/datas.py`  
**Usado por:** `repositories/viagem_repository.py`, `services/autorizacao_viagem_service.py`, `services/grupo_service.py`, `services/viagens_service.py`, `tests/test_funcionalidades.py`

---

## 7. Backend — Repositories

### `backend/repositories/__init__.py`  <small>(7 linhas)</small>

Reexporta os Repositories.

**Usa:** `repositories/favorito_repository.py`, `repositories/lugar_repository.py`, `repositories/relatorio_repository.py`  
**Usado por:** —

### `backend/repositories/favorito_repository.py`  <small>(31 linhas)</small>

Favoritos com o lugar já carregado (sem N+1), conjunto de ids salvos (para marcar cartões) e contagem.

**Estrutura**

- **Classe `FavoritoRepository`**
  - `__init__(sessao)`
  - `listar_com_lugar(usuario_id)` — Favoritos já com o Lugar carregado (evita N+1).
  - `ids_favoritados(usuario_id)` — Conjunto de ids de lugares salvos — usado para marcar os cartões na listagem.
  - `contar_por_usuario(usuario_id)`

**Usa:** `extensions.py`, `models/favorito.py`  
**Usado por:** `services/assistente_service.py`, `services/buscar_lugares_service.py`, `services/comparador_service.py`, `services/listar_favoritos_service.py`, `services/listar_lugares_service.py`, `services/obter_perfil_service.py`, `services/recomendar_lugares_service.py`

### `backend/repositories/lugar_repository.py`  <small>(134 linhas)</small>

Consultas SQL de lugares: busca com filtros combinados e popularidade (contagem de favoritos), candidatos à recomendação, contagem por categoria e estados disponíveis. `_hidratar` transforma linhas `(id, popularidade)` em objetos `Lugar` preservando a ordem.

**Estrutura**

- **Classe `LugarRepository`** — Repository de acesso a dados de lugares.
  - `__init__(sessao)`
  - `buscar_com_filtros(categoria, texto, faixa_preco_maxima, estado, nota_minima, ordenar_por, limite)`
  - `buscar_candidatos_para_recomendacao(categorias, faixa_preco_maxima, limite)` — Traz lugares das categorias de interesse (ou todos) com sua popularidade.
  - `contar_por_categoria()`
  - `listar_estados_disponiveis()`
  - `_hidratar(linhas)` — Converte as linhas (id, popularidade) em objetos Lugar preservando a ordem.

**Usa:** `extensions.py`, `models/lugar.py`  
**Usado por:** `services/buscar_lugares_service.py`, `services/gerar_relatorio_service.py`, `services/listar_lugares_service.py`, `services/recomendar_lugares_service.py`

### `backend/repositories/relatorio_repository.py`  <small>(82 linhas)</small>

Agregações do relatório; no MySQL chama a Stored Procedure, nos demais bancos usa SQL equivalente.

**Estrutura**

- **Classe `RelatorioRepository`**
  - `__init__(sessao)`
  - `usando_mysql()`
  - `ranking_destinos_mais_salvos(limite)` — Ranking dos lugares mais salvos pelos usuários.
  - `interesses_mais_escolhidos()`
  - `estatisticas_gerais()`

**Usa:** `config.py`, `extensions.py`  
**Usado por:** `services/gerar_relatorio_service.py`

### `backend/repositories/viagem_repository.py`  <small>(72 linhas)</small>

Viagens do usuário (como dono **ou** participante que aceitou), resumo agregado de uma viagem (gasto, checklist, compromissos, roteiro) e `viagem_concluida_com_lugar`, que sustenta o selo "viagem verificada".

**Estrutura**

- **Classe `ViagemRepository`**
  - `__init__(sessao)`
  - `listar_do_usuario(usuario_id)` — Viagens que o usuário organiza ou das quais participa (convite aceito).
  - `resumo(viagem)`
  - `viagem_concluida_com_lugar(usuario_id, lugar_id, hoje)` — Primeira viagem concluída do usuário cujo destino ou roteiro ativo inclui o lugar.

**Usa:** `extensions.py`, `models/checklist.py`, `models/compromisso.py`, `models/despesa.py`, `models/roteiro.py`, `models/viagem.py`  
**Usado por:** `services/assistente_service.py`, `services/avaliacoes_service.py`, `services/diario_service.py`, `services/viagens_service.py`

---

## 8. Backend — Utils

### `backend/utils/__init__.py`  <small>(1 linhas)</small>

Arquivo vazio (marca o pacote).

**Usa:** —  
**Usado por:** `controllers/foto_controller.py`, `services/avaliacoes_service.py`, `services/diario_service.py`

### `backend/utils/arquivos.py`  <small>(131 linhas)</small>

Segurança de uploads. `salvar_imagem`: limita o tamanho, confere a **assinatura binária** (JPEG/PNG/WebP, não só a extensão), valida com Pillow, corrige a orientação, reduz a no máximo 1920 px e **regrava a imagem sem metadados (EXIF/GPS)**; o nome final é aleatório e o arquivo fica fora da pasta pública. `url_assinada`/`assinatura_valida`: o acesso é por URL com HMAC (SECRET_KEY) e validade.

**Estrutura**

- **Constantes:** `SUBPASTAS`, `RE_NOME`, `ASSINATURAS`
- **Função `_detectar_formato(cabecalho)`**
- **Função `pasta(subpasta, config)`**
- **Função `salvar_imagem(arquivo, subpasta, config)`** — Valida e grava um FileStorage do Flask. Devolve o nome gerado.
- **Função `remover_imagem(subpasta, nome, config)`**
- **Função `_assinatura(subpasta, nome, expira, chave)`**
- **Função `url_assinada(subpasta, nome, config)`**
- **Função `assinatura_valida(subpasta, nome, expira, assinatura, config)`**

**Usa:** `config.py`, `utils/erros.py`  
**Usado por:** `controllers/foto_controller.py`, `models/avaliacao.py`, `models/diario.py`, `services/avaliacoes_service.py`, `services/diario_service.py`, `tests/test_funcionalidades.py`

### `backend/utils/autenticacao.py`  <small>(32 linhas)</small>

Lê o token do cabeçalho `Authorization: Bearer` (ou `X-Token`), busca o usuário e oferece o decorador `@login_obrigatorio`.

**Estrutura**

- **Função `usuario_do_token()`**
- **Função `login_obrigatorio(funcao)`** — Decorator usado nas Controllers para rotas protegidas.

**Usa:** `models/usuario.py`, `utils/erros.py`  
**Usado por:** `controllers/auth_controller.py`, `controllers/avaliacao_controller.py`, `controllers/calendario_controller.py`, `controllers/chat_controller.py`, `controllers/checklist_controller.py`, `controllers/comparador_controller.py`, `controllers/despesa_controller.py`, `controllers/diario_controller.py`, `controllers/favorito_controller.py`, `controllers/grupo_controller.py`, `controllers/lugar_controller.py`, `controllers/mapa_controller.py` e mais 4

### `backend/utils/datas.py`  <small>(25 linhas)</small>

Data/hora em UTC "ingênuo" (compatível com o SQLite) e funções de apoio (`hoje`, `formatar_data`).

**Estrutura**

- **Função `agora_utc()`** — Momento atual em UTC, sem informação de fuso.
- **Função `hoje()`** — Data local de hoje (as viagens são planejadas em datas do calendário local).
- **Função `formatar_data(valor)`**

**Usa:** —  
**Usado por:** `models/avaliacao.py`, `models/cache_externo.py`, `models/checklist.py`, `models/codigo_verificacao.py`, `models/compromisso.py`, `models/despesa.py`, `models/diario.py`, `models/favorito.py`, `models/foto_lugar.py`, `models/lugar.py`, `models/mensagem_chat.py`, `models/migracao.py` e mais 12

### `backend/utils/erros.py`  <small>(53 linhas)</small>

Hierarquia de exceções de domínio (`ErroDeAplicacao` e filhas) com o status HTTP de cada uma; o `app.py` as converte em JSON `{erro, campo}`.

**Estrutura**

- **Classe `ErroDeAplicacao`** (Exception)
  - `__init__(mensagem, campo, status)`
  - `to_dict()`
- **Classe `ErroDeValidacao`** (ErroDeAplicacao)
- **Classe `ErroDeNegocio`** (ErroDeAplicacao)
- **Classe `NaoAutorizado`** (ErroDeAplicacao)
- **Classe `NaoEncontrado`** (ErroDeAplicacao)
- **Classe `ConflitoDeDados`** (ErroDeAplicacao)
- **Classe `AcessoNegado`** (ErroDeAplicacao)
- **Classe `LimiteExcedido`** (ErroDeAplicacao)
- **Classe `IntegracaoIndisponivel`** (ErroDeAplicacao) — Serviço externo desligado, sem credencial ou fora do ar.

**Usa:** —  
**Usado por:** `app.py`, `controllers/comparador_controller.py`, `services/autenticar_usuario_service.py`, `services/autorizacao_viagem_service.py`, `services/avaliacoes_service.py`, `services/cadastrar_usuario_service.py`, `services/calendario_service.py`, `services/checklist_service.py`, `services/comparador_service.py`, `services/diario_service.py`, `services/enviar_mensagem_chat_service.py`, `services/financas_service.py` e mais 24

### `backend/utils/geo.py`  <small>(56 linhas)</small>

Coordenadas das cidades atendidas, distância de Haversine e a lista de cidades (com a capitalização corrigida: "Rio de Janeiro").

**Estrutura**

- **Constantes:** `CIDADES`, `PADRAO`
- **Função `coordenadas_da_cidade(cidade, estado)`** — Retorna (lat, lon) da cidade informada; cai no padrão quando desconhecida.
- **Função `distancia_km(origem, destino)`** — Distância de grande círculo (fórmula de Haversine), em quilômetros.
- **Função `_nome_proprio(nome)`** — 'rio de janeiro' -> 'Rio de Janeiro' (preposições em minúsculas).
- **Função `listar_cidades()`**

**Usa:** —  
**Usado por:** `services/calcular_match_service.py`, `services/comparador_service.py`, `services/integracoes/fotos_wikimedia_service.py`, `services/integracoes/pontos_interesse_service.py`, `services/listar_interesses_service.py`, `services/mapa_service.py`, `services/roteiro_inteligente_service.py`, `tests/test_regras.py`

### `backend/utils/limite_requisicoes.py`  <small>(57 linhas)</small>

Limitador de requisições por janela deslizante em memória, por usuário (ou IP). Decorador `@limitar(nome, máximo, janela)`. Em produção com vários servidores trocaria o armazenamento por um compartilhado (ex.: Redis).

**Estrutura**

- **Função `_identidade()`**
- **Função `verificar_limite(chave, maximo, janela_segundos)`**
- **Função `limitar(nome, maximo, janela_segundos)`** — Decorator: no máximo `maximo` chamadas por usuário/IP a cada `janela_segundos`.
- **Função `limpar_limites()`**

**Usa:** `utils/erros.py`  
**Usado por:** `controllers/auth_controller.py`, `controllers/avaliacao_controller.py`, `controllers/chat_controller.py`, `controllers/comparador_controller.py`, `controllers/diario_controller.py`, `controllers/grupo_controller.py`, `controllers/mapa_controller.py`, `controllers/roteiro_controller.py`, `controllers/viagem_controller.py`, `tests/apoio.py`, `tests/test_funcionalidades.py`

### `backend/utils/requisicao.py`  <small>(16 linhas)</small>

`dados_e_fotos()` lê o corpo como JSON **ou** formulário multipart (campos + arquivos `fotos`); `corpo_json()` garante um dicionário.

**Estrutura**

- **Função `dados_e_fotos()`** — Devolve (dados, fotos). Em multipart, os campos vêm do formulário e as fotos de 'fotos'.
- **Função `corpo_json()`**

**Usa:** —  
**Usado por:** `controllers/avaliacao_controller.py`, `controllers/calendario_controller.py`, `controllers/checklist_controller.py`, `controllers/despesa_controller.py`, `controllers/diario_controller.py`, `controllers/grupo_controller.py`, `controllers/roteiro_controller.py`, `controllers/viagem_controller.py`

### `backend/utils/validadores.py`  <small>(202 linhas)</small>

Funções de validação reutilizadas pelos Services. As originais cobrem nome, e-mail, senha, código e orçamento; as novas cobrem texto com limites, inteiros, **dinheiro** (aceita `1.234,56`, `1234.56` e números; devolve centavos), datas ISO, horas HH:MM, data-hora, escolhas, coordenadas e booleanos, além de conversão hora↔minutos.

**Estrutura**

- **Constantes:** `REGEX_EMAIL`, `RE_HORA`
- **Função `validar_nome(nome)`**
- **Função `validar_email(email)`** — Valida o formato do e-mail. Levanta ErroDeValidacao quando inválido.
- **Função `validar_senha(senha, confirmacao)`** — Senha com no mínimo SENHA_TAMANHO_MINIMO (6) caracteres.
- **Função `validar_codigo(codigo)`**
- **Função `validar_orcamento(orcamento)`**
- **Função `validar_texto(valor, campo, rotulo, minimo, maximo, obrigatorio)`**
- **Função `validar_inteiro(valor, campo, rotulo, minimo, maximo, obrigatorio)`**
- **Função `validar_valor_monetario(valor, campo, rotulo, obrigatorio, maximo)`** — Converte "1.234,56", "1234.56" ou 1234.56 em centavos (int).
- **Função `validar_data(valor, campo, rotulo, obrigatorio)`**
- **Função `validar_hora(valor, campo, rotulo, obrigatorio)`**
- **Função `validar_data_hora(valor, campo, rotulo)`**
- **Função `validar_escolha(valor, opcoes, campo, rotulo, padrao)`**
- **Função `validar_coordenadas(latitude, longitude, obrigatorio)`**
- **Função `validar_booleano(valor)`**
- **Função `hora_para_minutos(hora)`**
- **Função `minutos_para_hora(minutos)`**

**Usa:** `config.py`, `utils/erros.py`  
**Usado por:** `services/assistente_service.py`, `services/autenticar_usuario_service.py`, `services/avaliacoes_service.py`, `services/cadastrar_usuario_service.py`, `services/calendario_service.py`, `services/checklist_service.py`, `services/diario_service.py`, `services/financas_service.py`, `services/grupo_service.py`, `services/reenviar_codigo_service.py`, `services/roteiro_inteligente_service.py`, `services/roteiros_service.py` e mais 4

---

## 9. Backend — Testes

### `backend/tests/__init__.py`  <small>(1 linhas)</small>

Arquivo vazio (marca o pacote).

### `backend/tests/apoio.py`  <small>(91 linhas)</small>

Infraestrutura dos testes de integração: pasta temporária de uploads, configuração isolada (SQLite temporário, integrações externas e limitador desligados), `CasoComApp` (cria o app, usuários verificados com e-mail único) e `imagem_png`.

**Estrutura**

- **Constantes:** `_PASTA_TEMP`
- **Função `criar_config(banco)`**
- **Função `imagem_png(largura, altura, cor)`**
- **Classe `CasoComApp`** (unittest.TestCase) — Cria um banco SQLite novo por classe de teste.
  - `setUpClass(cls)`
  - `tearDownClass(cls)`
  - `requisitar(metodo, caminho, token, json, **kwargs)`
  - `criar_usuario(nome, email, senha, preferencias, interesses, cidade, estado)`
  - `lugar_por_nome(nome)`

**Usa:** `app.py`, `config.py`, `extensions.py`, `models/lugar.py`, `utils/limite_requisicoes.py`  
**Usado por:** `tests/test_funcionalidades.py`

### `backend/tests/test_funcionalidades.py`  <small>(850 linhas)</small>

24 testes da API completa. Os de Wikimedia e Gemini usam **respostas simuladas** (indicado nos nomes); os demais exercitam o app de verdade com banco temporário.

**Estrutura**

- **Constantes:** `HOJE`
- **Função `d(dias)`**
- **Classe `TestCompatibilidade`** (CasoComApp) — Funcionalidades antigas continuam funcionando.
  - `test_fluxo_original()`
  - `test_cabecalhos_de_seguranca()`
- **Classe `TestPlanejador`** (CasoComApp)
  - `test_crud_e_status()`
  - `test_validacoes()`
- **Classe `TestGrupoEPermissoes`** (CasoComApp)
  - `test_convites_papeis_e_isolamento()`
- **Classe `TestRoteiros`** (CasoComApp)
  - `test_gerar_versionar_e_editar()`
  - `test_pontos_reais_do_openstreetmap_e_funcionamento()` — Pontos OSM já em cache entram no roteiro; horário de funcionamento é respeitado.
  - `test_ia_nao_pode_inventar_lugares()` — Gemini simulado: itens fora da lista de candidatos são descartados.
- **Classe `TestFinancas`** (CasoComApp)
  - `test_orcamento_despesas_e_alertas()`
- **Classe `TestChecklist`** (CasoComApp)
  - `test_sugestoes_progresso_e_reuso()`
- **Classe `TestCalendario`** (CasoComApp)
  - `test_agenda_integra_roteiro_e_detecta_conflitos()`
- **Classe `TestAvaliacoes`** (CasoComApp)
  - `test_avaliar_com_fotos_sem_duplicar()`
  - `test_exif_gps_removido()`
- **Classe `TestDiario`** (CasoComApp)
  - `test_registros_visibilidade_e_estatisticas()`
- **Classe `ClienteFalso`** — Simula as respostas da API da Wikimedia (sem rede).
  - `__init__(respostas)`
  - `requisitar_json(url, params, **_)`
- **Função `_info(titulo, licenca, largura, altura)`**
- **Classe `TestFotosReais`** (CasoComApp)
  - `test_sincronizacao_wikimedia_simulada_e_curadoria()`
  - `test_coordenadas_divergentes_nao_verificam()` — Artigo homônimo longe do lugar real não é aceito.
  - `test_sem_rede_nao_quebra()`
- **Classe `TestFundoInicial`** (unittest.TestCase)
  - `test_versoes_otimizadas_do_fundo()` — tools/fotos.py fundo: paisagens 960/1600/2400 + recorte vertical 9:16 (imagem sintética).
- **Classe `TestMapaEComparador`** (CasoComApp)
  - `test_mapa_da_viagem()`
  - `test_comparador()`
- **Classe `TestVai`** (CasoComApp)
  - `test_permissoes_contexto_e_acoes()`
- **Classe `TestSeguranca`** (CasoComApp)
  - `test_limite_de_requisicoes()`
  - `test_envio_grande_demais()`
- **Classe `TestMigracaoBancoExistente`** (unittest.TestCase)
  - `test_banco_antigo_e_preservado()` — Um banco criado pela versão anterior ganha as tabelas novas sem perder dados.

**Testes**

- **TestCompatibilidade**
  - `test_fluxo_original`
  - `test_cabecalhos_de_seguranca`
- **TestPlanejador**
  - `test_crud_e_status`
  - `test_validacoes`
- **TestGrupoEPermissoes**
  - `test_convites_papeis_e_isolamento`
- **TestRoteiros**
  - `test_gerar_versionar_e_editar`
  - `test_pontos_reais_do_openstreetmap_e_funcionamento`
  - `test_ia_nao_pode_inventar_lugares`
- **TestFinancas**
  - `test_orcamento_despesas_e_alertas`
- **TestChecklist**
  - `test_sugestoes_progresso_e_reuso`
- **TestCalendario**
  - `test_agenda_integra_roteiro_e_detecta_conflitos`
- **TestAvaliacoes**
  - `test_avaliar_com_fotos_sem_duplicar`
  - `test_exif_gps_removido`
- **TestDiario**
  - `test_registros_visibilidade_e_estatisticas`
- **TestFotosReais**
  - `test_sincronizacao_wikimedia_simulada_e_curadoria`
  - `test_coordenadas_divergentes_nao_verificam`
  - `test_sem_rede_nao_quebra`
- **TestFundoInicial**
  - `test_versoes_otimizadas_do_fundo`
- **TestMapaEComparador**
  - `test_mapa_da_viagem`
  - `test_comparador`
- **TestVai**
  - `test_permissoes_contexto_e_acoes`
- **TestSeguranca**
  - `test_limite_de_requisicoes`
  - `test_envio_grande_demais`
- **TestMigracaoBancoExistente**
  - `test_banco_antigo_e_preservado`

**Usa:** `app.py`, `extensions.py`, `models/avaliacao.py`, `models/foto_lugar.py`, `models/lugar.py`, `models/ponto_interesse.py`, `models/viagem.py`, `services/fotos_lugar_service.py`, `services/integracoes/fotos_wikimedia_service.py`, `services/roteiro_inteligente_service.py`, `tests/apoio.py`, `utils/arquivos.py` e mais 2  
**Usado por:** —

### `backend/tests/test_regras.py`  <small>(125 linhas)</small>

Testes originais das regras que não dependem do banco: validadores, distância, match e assistente local.

**Estrutura**

- **Função `checar(condicao, descricao)`**
- **Função `levanta(funcao, *args)`**
- **Função `testar_validacoes()`**
- **Função `testar_distancias()`**
- **Função `_lugar(categoria, nota, preco, popularidade)`**
- **Função `_preferencia(interesses, orcamento)`**
- **Função `testar_match()`**
- **Função `testar_assistente_local()`**

**Usa:** `services/assistente_local_service.py`, `services/calcular_match_service.py`, `utils/erros.py`, `utils/geo.py`, `utils/validadores.py`  
**Usado por:** —

---

## 10. Frontend — Páginas HTML

### `frontend/app.html`  <small>(175 linhas)</small>

Tela principal com abas Início, Explorar, Salvos e Perfil, modal de detalhes do lugar, atalhos para as novas áreas e botão do mapa geral.

**Título:** Início · Viajaí  
**Estilos:** `vendor/leaflet/leaflet.css`, `css/estilos.css`  
**Scripts (ordem de carga):** `vendor/leaflet/leaflet.js`, `js/api.js`, `js/ui.js`, `js/app.js`  
**Elementos com id:** 50 — `#saudacao`, `#nome-usuario`, `#atalho-salvos`, `#avatar`, `#entrada-busca`, `#botao-filtros`, `#filtros`, `#aba-inicio`, `#contador-convites`, `#ver-todos`, `#destaques`, `#contador-lugares`, `#lista-lugares`, `#aba-explorar`…

### `frontend/cadastro.html`  <small>(121 linhas)</small>

Cadastro em duas etapas (dados e código de 6 dígitos), com medidor de força da senha.

**Título:** Criar conta · Viajaí  
**Estilos:** `css/estilos.css`  
**Scripts (ordem de carga):** `js/api.js`, `js/validacoes.js`, `js/cadastro.js`  
**Elementos com id:** 25 — `#botao-voltar`, `#etapa-dados`, `#alerta-dados`, `#form-dados`, `#campo-nome`, `#nome`, `#campo-email`, `#email`, `#campo-senha`, `#senha`, `#ver-senha`, `#forca`, `#regras`, `#campo-confirmacao`…

### `frontend/chat.html`  <small>(49 linhas)</small>

Conversa com o Vai, com seletor de viagem em foco e botão de permissões.

**Título:** Vai · Assistente de viagem  
**Estilos:** `css/estilos.css`  
**Scripts (ordem de carga):** `js/api.js`, `js/ui.js`, `js/chat.js`  
**Elementos com id:** 10 — `#botao-voltar`, `#selo-ia`, `#foco-viagem`, `#botao-permissoes`, `#mensagens`, `#dia`, `#sugestoes`, `#form-chat`, `#entrada`, `#botao-enviar`

### `frontend/comparar.html`  <small>(34 linhas)</small>

Seleção e comparação de destinos.

**Título:** Comparar destinos · Viajaí  
**Estilos:** `css/estilos.css`  
**Scripts (ordem de carga):** `js/api.js`, `js/ui.js`, `js/comparar.js`  
**Elementos com id:** 5 — `#botao-voltar`, `#escolhidos`, `#filtro`, `#lista`, `#resultado`

### `frontend/comunidade.html`  <small>(25 linhas)</small>

Feed da comunidade.

**Título:** Comunidade · Viajaí  
**Estilos:** `css/estilos.css`  
**Scripts (ordem de carga):** `js/api.js`, `js/ui.js`, `js/comunidade.js`  
**Elementos com id:** 2 — `#botao-voltar`, `#feed`

### `frontend/diario.html`  <small>(27 linhas)</small>

Estatísticas e linha do tempo do diário.

**Título:** Diário de viagens · Viajaí  
**Estilos:** `css/estilos.css`  
**Scripts (ordem de carga):** `js/api.js`, `js/ui.js`, `js/formulario-viagem.js`, `js/diario.js`  
**Elementos com id:** 4 — `#botao-voltar`, `#novo-registro`, `#estatisticas`, `#linha-tempo`

### `frontend/index.html`  <small>(55 linhas)</small>

Tela de boas-vindas. Mantém marca, aviso, chips, título e botões; ganhou a camada `#fundo` (foto real) e o crédito. O script `inicio.js` preenche a foto; sem ela, o fundo de reserva do CSS continua valendo.

**Título:** Viajaí · Descubra o mundo do seu jeito  
**Estilos:** `css/estilos.css`  
**Scripts (ordem de carga):** `js/api.js`, `js/ui.js`, `js/inicio.js`  
**Elementos com id:** 5 — `#fundo`, `#aviso`, `#fechar-aviso`, `#local-foto`, `#credito-fundo`

### `frontend/interesses.html`  <small>(55 linhas)</small>

Escolha de interesses, orçamento e cidade.

**Título:** Seus interesses · Viajaí  
**Estilos:** `css/estilos.css`  
**Scripts (ordem de carga):** `js/api.js`, `js/interesses.js`  
**Elementos com id:** 6 — `#alerta`, `#grade-interesses`, `#orcamento`, `#descricao-orcamento`, `#cidade`, `#botao-salvar`

### `frontend/login.html`  <small>(57 linhas)</small>

Login por e-mail e senha.

**Título:** Entrar · Viajaí  
**Estilos:** `css/estilos.css`  
**Scripts (ordem de carga):** `js/api.js`, `js/validacoes.js`, `js/login.js`  
**Elementos com id:** 9 — `#botao-voltar`, `#alerta`, `#form-login`, `#campo-email`, `#email`, `#campo-senha`, `#senha`, `#ver-senha`, `#botao-entrar`

### `frontend/lugar.html`  <small>(31 linhas)</small>

Página do lugar: galeria, informações, mapa e avaliações (tudo montado por `lugar.js`).

**Título:** Lugar · Viajaí  
**Estilos:** `vendor/leaflet/leaflet.css`, `css/estilos.css`  
**Scripts (ordem de carga):** `vendor/leaflet/leaflet.js`, `js/api.js`, `js/ui.js`, `js/lugar.js`  
**Elementos com id:** 4 — `#galeria`, `#botao-voltar`, `#botao-favorito`, `#conteudo`

### `frontend/viagem.html`  <small>(44 linhas)</small>

Painel da viagem. É só a casca: o conteúdo de cada aba é montado pelos scripts `viagem-*.js`.

**Título:** Viagem · Viajaí  
**Estilos:** `vendor/leaflet/leaflet.css`, `css/estilos.css`  
**Scripts (ordem de carga):** `vendor/leaflet/leaflet.js`, `js/api.js`, `js/ui.js`, `js/formulario-viagem.js`, `js/viagem.js`, `js/viagem-roteiro.js`, `js/viagem-agenda.js`, `js/viagem-gastos.js`, `js/viagem-checklist.js`, `js/viagem-mapa.js`, `js/viagem-grupo.js`  
**Elementos com id:** 8 — `#botao-voltar`, `#titulo-pagina`, `#abrir-vai`, `#editar-viagem`, `#excluir-viagem`, `#capa`, `#abas`, `#painel`

### `frontend/viagens.html`  <small>(38 linhas)</small>

Lista de viagens com filtros por status e área de convites.

**Título:** Minhas viagens · Viajaí  
**Estilos:** `css/estilos.css`  
**Scripts (ordem de carga):** `js/api.js`, `js/ui.js`, `js/formulario-viagem.js`, `js/viagens.js`  
**Elementos com id:** 3 — `#nova-viagem`, `#convites`, `#lista-viagens`

---

## 11. Frontend — Estilo

### `frontend/css/estilos.css`  <small>(870 linhas)</small>

Folha de estilos única. A primeira parte é a original (tokens de cor `--laranja`, `--tinta`..., telas de entrada, home, chat, modal). A segunda, marcada "EXPANSÃO", acrescenta: foco visível, botões, abas, toasts, folhas modais, estados vazios, KPIs, roteiro, agenda, gastos, checklist, mapa, grupo, galeria/lightbox, avaliações, comparador, diário e o fundo da tela inicial (com ajustes para tablet e desktop). Respeita `prefers-reduced-motion`.

**Variáveis de tema:** `--laranja: #ff6b35`, `--laranja-escuro: #e85a25`, `--laranja-claro: #fff1ea`, `--tinta: #16232f`, `--tinta-media: #5b6b7a`, `--tinta-fraca: #93a1ad`, `--fundo: #f7f5f2`, `--branco: #ffffff`, `--borda: #e8e4de`, `--verde: #16a34a`, `--azul: #2f80ed`, `--vermelho: #d92d20`, `--raio: 18px`, `--raio-g: 26px`

**Classes distintas:** 259

---

## 12. Frontend — JavaScript

### `frontend/js/api.js`  <small>(216 linhas)</small>

**Única camada de comunicação com o backend.** `Sessao` guarda token e usuário no navegador; `requisitar()` monta a chamada (JSON ou FormData), trata erro de rede, resposta inválida e 401 (limpa a sessão e volta ao login); `Api` tem uma função por endpoint; `urlCapa` escolhe foto real ou ilustração.

**Funções da `Api` e o endpoint que cada uma chama**

| Função | Requisição |
|---|---|
| `Api.cadastrar` | `POST /api/auth/cadastro` |
| `Api.verificarCodigo` | `POST /api/auth/verificar` |
| `Api.reenviarCodigo` | `POST /api/auth/reenviar-codigo` |
| `Api.entrar` | `POST /api/auth/login` |
| `Api.sair` | `POST /api/auth/logout` |
| `Api.perfil` | `GET /api/usuarios/eu` |
| `Api.opcoesPreferencias` | `GET /api/preferencias/opcoes` |
| `Api.salvarPreferencias` | `PUT /api/preferencias` |
| `Api.listarLugares` | `GET /api/lugares${categoria && categoria !== ` |
| `Api.buscarLugares` | `GET /api/lugares/busca?:id` |
| `Api.detalharLugar` | `GET /api/lugares/:id` |
| `Api.listarFavoritos` | `GET /api/favoritos` |
| `Api.salvarFavorito` | `POST /api/favoritos` |
| `Api.removerFavorito` | `DELETE /api/favoritos/:id` |
| `Api.historicoChat` | `GET /api/chat` |
| `Api.permissoesVai` | `GET /api/chat/permissoes` |
| `Api.salvarPermissoesVai` | `PUT /api/chat/permissoes` |
| `Api.listarViagens` | `GET /api/viagens${status ? ` |
| `Api.criarViagem` | `POST /api/viagens` |
| `Api.viagem` | `GET /api/viagens/:id` |
| `Api.editarViagem` | `PUT /api/viagens/:id` |
| `Api.excluirViagem` | `DELETE /api/viagens/:id` |
| `Api.roteiros` | `GET /api/viagens/:id/roteiros` |
| `Api.gerarRoteiro` | `POST /api/viagens/:id/roteiros/gerar` |
| `Api.criarRoteiro` | `POST /api/viagens/:id/roteiros` |
| `Api.roteiro` | `GET /api/roteiros/:id` |
| `Api.duplicarRoteiro` | `POST /api/roteiros/:id/duplicar` |
| `Api.ativarRoteiro` | `POST /api/roteiros/:id/ativar` |
| `Api.excluirRoteiro` | `DELETE /api/roteiros/:id` |
| `Api.reorganizarRoteiro` | `PUT /api/roteiros/:id/ordem` |
| `Api.adicionarAtividade` | `POST /api/roteiros/:id/atividades` |
| `Api.editarAtividade` | `PATCH /api/atividades/:id` |
| `Api.excluirAtividade` | `DELETE /api/atividades/:id` |
| `Api.financas` | `GET /api/viagens/:id/financas` |
| `Api.definirOrcamento` | `PUT /api/viagens/:id/orcamento` |
| `Api.registrarDespesa` | `POST /api/viagens/:id/despesas` |
| `Api.editarDespesa` | `PUT /api/despesas/:id` |
| `Api.excluirDespesa` | `DELETE /api/despesas/:id` |
| `Api.checklist` | `GET /api/viagens/:id/checklist` |
| `Api.sugerirChecklist` | `POST /api/viagens/:id/checklist/sugestoes` |
| `Api.adicionarItem` | `POST /api/viagens/:id/checklist` |
| `Api.atualizarItem` | `PATCH /api/checklist/:id` |
| `Api.removerItem` | `DELETE /api/checklist/:id` |
| `Api.calendario` | `GET /api/viagens/:id/calendario` |
| `Api.criarCompromisso` | `POST /api/viagens/:id/compromissos` |
| `Api.editarCompromisso` | `PUT /api/compromissos/:id` |
| `Api.excluirCompromisso` | `DELETE /api/compromissos/:id` |
| `Api.participantes` | `GET /api/viagens/:id/participantes` |
| `Api.convidar` | `POST /api/viagens/:id/participantes` |
| `Api.removerParticipante` | `DELETE /api/viagens/:id/participantes/:id` |
| `Api.convites` | `GET /api/convites` |
| `Api.aceitarConvite` | `POST /api/convites/:id/aceitar` |
| `Api.recusarConvite` | `POST /api/convites/:id/recusar` |
| `Api.sugestoes` | `GET /api/viagens/:id/sugestoes` |
| `Api.sugerir` | `POST /api/viagens/:id/sugestoes` |
| `Api.votar` | `POST /api/sugestoes/:id/voto` |
| `Api.decidir` | `POST /api/sugestoes/:id/decisao` |
| `Api.avaliacoes` | `GET /api/lugares/:id/avaliacoes?ordenar=:id` |
| `Api.avaliar` | `POST /api/lugares/:id/avaliacoes` |
| `Api.editarAvaliacao` | `PUT /api/avaliacoes/:id` |
| `Api.excluirAvaliacao` | `DELETE /api/avaliacoes/:id` |
| `Api.removerFotoAvaliacao` | `DELETE /api/avaliacoes/:id/fotos/:id` |
| `Api.comunidade` | `GET /api/comunidade` |
| `Api.diario` | `GET /api/diario` |
| `Api.estatisticas` | `GET /api/diario/estatisticas` |
| `Api.criarRegistro` | `POST /api/diario` |
| `Api.editarRegistro` | `PUT /api/diario/:id` |
| `Api.excluirRegistro` | `DELETE /api/diario/:id` |
| `Api.removerFotoRegistro` | `DELETE /api/diario/:id/fotos/:id` |
| `Api.diarioDaViagem` | `GET /api/viagens/:id/diario` |
| `Api.fotosLugar` | `GET /api/lugares/:id/fotos` |
| `Api.fundoInicial` | `GET /api/vitrine/fundo` |
| `Api.configMapa` | `GET /api/mapa/config` |
| `Api.lugaresMapa` | `GET /api/mapa/lugares` |
| `Api.mapaViagem` | `GET /api/viagens/:id/mapa` |
| `Api.proximidades` | `GET /api/lugares/:id/proximidades?raio_km=:id` |
| `Api.comparar` | `GET /api/comparador?ids=${ids.join(` |

**Estrutura**

- **`Sessao`** (objeto/classe de nível superior)
- **`ErroApi`** (objeto/classe de nível superior)
- **`Api`** (objeto/classe de nível superior)
- `requisitar(caminho, { metodo = "GET", corpo = null, autenticado = true, formulario = null } = {})`
- `mostrarAlerta(elemento, mensagem, tipo = "erro")` — Utilidades de interface --------------------------------------------------
- `esconderAlerta(elemento)`
- `urlImagem(nomeArquivo)`
- `urlCapa(lugar, tamanho = "miniatura")` — Imagem do cartão: fotografia real verificada quando houver; senão, a ilustração da categoria.

### `frontend/js/app.js`  <small>(354 linhas)</small>

Tela principal: carrega perfil e recomendações, filtros, busca com *debounce*, favoritos, modal de detalhes (com crédito da foto e links para a página do lugar e planejamento), abas por *hash* (`#perfil`), resumo de viagens e o **mapa geral** do catálogo.

**Estrutura**

- `iniciar()` — ---------------------------------------------------------------------
- `mostrarCabecalho()`
- `montarFiltros()` — ----------------------------- filtros --------------------------------
- `carregarInicio()` — ------------------------------ início --------------------------------
- `buscar()` — ------------------------------ busca ---------------------------------
- `abrirMapaGeral()` — Mapa com todo o catálogo: destinos e atrações (laranja) e restaurantes/estabelecimentos (azul).
- `carregarSalvos(renderizar = true)` — ----------------------------- favoritos -------------------------------
- `alternarFavorito(lugar, botao)`
- `cartaoDestaque(lugar)` — ------------------------------ cartões --------------------------------
- `cartaoLista(lugar)`
- `mensagemVazia(icone, texto)`
- `abrirDetalhes(lugar)` — ------------------------------ detalhes -------------------------------
- `atualizarCoracao(lugar)` — Sincroniza o ♥ do cartão de destaque correspondente ao lugar.
- `montarNavegacao()` — ------------------------------ navegação ------------------------------
- `abrirAbaDoEndereco()` — Permite que outras telas abram uma aba específica (app.html#salvos, #perfil...).
- `carregarResumoViagens()`
- `trocarAba(aba)`
- `preencherPerfil()` — ------------------------------- perfil --------------------------------

**Endpoints que usa:** `buscarLugares` → GET /api/lugares/busca?:id; `listarFavoritos` → GET /api/favoritos; `listarViagens` → GET /api/viagens${status ? ; `lugaresMapa` → GET /api/mapa/lugares; `perfil` → GET /api/usuarios/eu; `recomendacoes` → ?; `removerFavorito` → DELETE /api/favoritos/:id; `sair` → POST /api/auth/logout; `salvarFavorito` → POST /api/favoritos

### `frontend/js/cadastro.js`  <small>(204 linhas)</small>

Fluxo do cadastro: validação em tempo real, envio, tela do código (6 campos com colar e navegação), reenviar código e voltar.

**Estrutura**

- **`campos`** (objeto/classe de nível superior)
- **`entradas`** (objeto/classe de nível superior)
- `validarCampo(nome, mostrarSucesso = true)` — ------------------------- validação em tempo real -------------------------
- `atualizarForca(senha)`
- `irParaCodigo(resposta)`
- `limparCodigo()`
- `voltar()`

**Endpoints que usa:** `cadastrar` → POST /api/auth/cadastro; `reenviarCodigo` → POST /api/auth/reenviar-codigo; `verificarCodigo` → POST /api/auth/verificar

### `frontend/js/chat.js`  <small>(159 linhas)</small>

Chat do Vai: histórico, sugestões rápidas, indicador de digitação, **seletor de viagem em foco**, janela de **permissões** e botões de **ações** devolvidos pelo assistente (criar viagem, gerar roteiro, abrir abas).

**Estrutura**

- `carregarViagens()` — Viagem em foco: escolher uma viagem autoriza o Vai a usar os dados dela nesta conversa.
- `abrirPermissoes()`
- `mostrarAcoes(acoes)`
- `executarAcao(acao)`
- `carregarHistorico()`
- `montarSugestoes(sugestoes)`
- `adicionarMensagem(autor, texto)`
- `mostrarDigitando()`
- `enviar(texto)`

**Endpoints que usa:** `enviarMensagem` → ?; `historicoChat` → GET /api/chat; `listarViagens` → GET /api/viagens${status ? ; `permissoesVai` → GET /api/chat/permissoes; `salvarPermissoesVai` → PUT /api/chat/permissoes

### `frontend/js/comparar.js`  <small>(103 linhas)</small>

Comparador: escolha dos destinos (máx. 3, via URL `?ids=`), busca no catálogo e quadro comparativo com a vantagem de cada critério.

**Estrutura**

- `iniciar()`
- `normalizar(t)`
- `desenharLista()`
- `alternar(id)`
- `atualizar()`
- `desenharComparacao(dados)`

**Endpoints que usa:** `comparar` → GET /api/comparador?ids=${ids.join(; `lugaresMapa` → GET /api/mapa/lugares

### `frontend/js/comunidade.js`  <small>(43 linhas)</small>

Feed misto de avaliações recentes e relatos públicos, com fotos ampliáveis.

**Estrutura**

- `carregar()`

**Endpoints que usa:** `comunidade` → GET /api/comunidade

### `frontend/js/diario.js`  <small>(148 linhas)</small>

Diário: estatísticas, linha do tempo por ano, formulário de memória (com fotos, visibilidade e nota) e exclusão.

**Estrutura**

- `carregar()`
- `desenharEstatisticas(e)`
- `desenharLinha()`
- `encontrar(id)`
- `formulario(atual = null, viagemId = null)`

**Endpoints que usa:** `criarRegistro` → POST /api/diario; `diario` → GET /api/diario; `editarRegistro` → PUT /api/diario/:id; `estatisticas` → GET /api/diario/estatisticas; `excluirRegistro` → DELETE /api/diario/:id; `listarViagens` → GET /api/viagens${status ? ; `removerFotoRegistro` → DELETE /api/diario/:id/fotos/:id

### `frontend/js/formulario-viagem.js`  <small>(116 linhas)</small>

Formulário de criar/editar viagem em uma folha modal; também expõe `catalogoLugares()` (cache dos lugares usado por outras telas).

**Estrutura**

- `catalogoLugares()`
- `abrirFormularioViagem({ viagem = null, lugarId = null } = {})` — * Abre a folha com o formulário. `viagem` (opcional) = edição. * Resolve com a viagem salva.

**Endpoints que usa:** `criarViagem` → POST /api/viagens; `editarViagem` → PUT /api/viagens/:id; `lugaresMapa` → GET /api/mapa/lugares

### `frontend/js/inicio.js`  <small>(66 linhas)</small>

Fundo da tela inicial: pede `/vitrine/fundo`, cria a imagem com `srcset` responsivo (e `<picture>` com recorte vertical para telas em pé), só mostra depois de carregada (transição suave) e exibe local e crédito. Se falhar, nada muda.

**Estrutura**

- `carregarFundo()` — * Busca no backend a melhor fotografia verificada para o fundo e a exibe com * srcset responsivo (o navegador escolhe a resolução certa para celular, tablet * o
- `mostrarCredito(dados)`

**Endpoints que usa:** `fundoInicial` → GET /api/vitrine/fundo

### `frontend/js/interesses.js`  <small>(129 linhas)</small>

Monta a grade de interesses, as faixas de orçamento e as cidades; preenche com as preferências atuais e salva.

**Estrutura**

- `iniciar()`
- `montarInteresses(interesses)`
- `montarOrcamentos(orcamentos)`
- `escolherOrcamento(valor)`
- `montarCidades(cidades)`
- `preencherComPreferenciasAtuais()`

**Endpoints que usa:** `opcoesPreferencias` → GET /api/preferencias/opcoes; `perfil` → GET /api/usuarios/eu; `salvarPreferencias` → PUT /api/preferencias

### `frontend/js/login.js`  <small>(50 linhas)</small>

Envio do login e redirecionamento (para interesses se ainda não há preferências).

**Endpoints que usa:** `entrar` → POST /api/auth/login

### `frontend/js/lugar.js`  <small>(304 linhas)</small>

Página do lugar: galeria (principal + miniaturas + lightbox, créditos), informações, mini-mapa com lugares/estabelecimentos próximos, "adicionar ao roteiro" e avaliações (resumo, distribuição, ordenação, publicar/editar/excluir com fotos).

**Estrutura**

- `iniciar()`
- `montarGaleria()` — ------------------------------ galeria ----------------------------------
- `alternarFavorito()`
- `montarConteudo()` — ----------------------------- conteúdo ----------------------------------
- `adicionarAoRoteiro()`
- `montarMapa()` — -------------------------------- mapa -----------------------------------
- `carregarAvaliacoes(ordenar = "recentes")` — ----------------------------- avaliações --------------------------------
- `cartaoAvaliacao(a)`
- `montarMinhaAvaliacao(minha)`
- `formularioAvaliacao(atual)`

**Endpoints que usa:** `adicionarAtividade` → POST /api/roteiros/:id/atividades; `avaliacoes` → GET /api/lugares/:id/avaliacoes?ordenar=:id; `avaliar` → POST /api/lugares/:id/avaliacoes; `criarRoteiro` → POST /api/viagens/:id/roteiros; `detalharLugar` → GET /api/lugares/:id; `editarAvaliacao` → PUT /api/avaliacoes/:id; `excluirAvaliacao` → DELETE /api/avaliacoes/:id; `listarViagens` → GET /api/viagens${status ? ; `proximidades` → GET /api/lugares/:id/proximidades?raio_km=:id; `removerFavorito` → DELETE /api/favoritos/:id; `removerFotoAvaliacao` → DELETE /api/avaliacoes/:id/fotos/:id; `roteiros` → GET /api/viagens/:id/roteiros; `salvarFavorito` → POST /api/favoritos

### `frontend/js/ui.js`  <small>(508 linhas)</small>

Biblioteca de interface sem dependências: `escapar`/`urlSegura` (proteção contra injeção de HTML), `Formato` (moeda, datas, km, duração), `toast`, `comCarregamento`, `Folha` (janelas deslizantes), `confirmar`, `lerFormulario`, `mostrarErroFormulario`, `telaVazia`, `imagemLugar` (carregamento sob demanda + fallback para ilustração), `Lightbox`, `campoFotos`, `estrelas`, `graficoRosca` (SVG), `navegacaoInferior`, e `criarMapa` (Leaflet com aviso se os tiles não carregarem).

**Estrutura**

- **`Formato`** (objeto/classe de nível superior)
- **`STATUS_VIAGEM`** (objeto/classe de nível superior)
- **`Folha`** (objeto/classe de nível superior)
- **`Lightbox`** (objeto/classe de nível superior)
- `escapar(valor)` — Escapa texto vindo do usuário ou de fontes externas antes de usar em innerHTML.
- `urlSegura(url)` — Só aceita links http(s) — evita "javascript:" em atributos href vindos de fora.
- `hojeIso()`
- `toast(mensagem, tipo = "ok")` — ------------------------------- toasts ---------------------------------
- `comCarregamento(botao, acao, textoCarregando = "Salvando...")` — Executa uma ação assíncrona com estado de carregamento no botão e toast de erro.
- `confirmar(mensagem, { textoConfirmar = "Confirmar", perigo = false } = {})`
- `lerFormulario(form)` — Lê os campos de um <form> em um objeto (checkbox → booleano).
- `mostrarErroFormulario(form, erro)` — Mostra o erro do backend no campo correspondente (ou no topo do formulário).
- `telaVazia(icone, titulo, texto, acao)` — --------------------------- estados de tela -----------------------------
- `esqueletos(quantidade = 3, altura = 92)`
- `imagemLugar(lugar, { tamanho = "miniatura", classe = "", alt, eager = false } = {})` — * <img> com lazy loading, decodificação assíncrona e fallback: se a fotografia * real falhar, troca pela ilustração da categoria (nunca deixa imagem quebrada).
- `creditoFoto(foto)`
- `miniaturasFotos(fotos, { removivel = false } = {})` — Miniaturas clicáveis de fotos enviadas pelos usuários (avaliações e diário).
- `ligarMiniaturas(raiz, fotos)`
- `campoFotos(nome = "fotos", maximo = 6)` — Campo de upload com pré-visualização e validação no navegador (o backend valida de novo).
- `estrelas(nota, maximo = 5)` — ----------------------------- estrelas ---------------------------------
- `seletorEstrelas(nome, valorInicial = 0)`
- `navegacaoInferior(ativa)` — --------------------------- navegação inferior --------------------------
- `ligarVoltar(botao, destino = "app.html")` — Botão "voltar" padrão: volta no histórico ou vai para um destino seguro.
- `graficoRosca(fatias, { tamanho = 150, espessura = 22, centro = "" } = {})` — Rosca em SVG (sem bibliotecas). fatias: [{valor, cor, rotulo}]
- `distanciaKm(a, b)` — Haversine — distância em linha reta (rotulada assim na interface).
- `criarMapa(elemento, { centro = [-15.8, -47.9], zoom = 4 } = {})` — Cria um mapa Leaflet com os tiles configurados no backend (com atribuição).
- `marcadorNumerado(numero, cor = "#ff6b35")`

**Endpoints que usa:** `configMapa` → GET /api/mapa/config

### `frontend/js/validacoes.js`  <small>(66 linhas)</small>

Validações do formulário de cadastro/login que espelham as do backend (nome, e-mail, senha, força da senha) e o estado visual dos campos.

**Estrutura**

- `validarNome(nome)`
- `validarEmail(email)`
- `validarSenha(senha)`
- `confirmarSenha(senha, confirmacao)`
- `forcaDaSenha(senha)` — Retorna 0 (vazia), 1 (fraca), 2 (média) ou 3 (forte).
- `aplicarEstado(campo, resultado, mostrarSucesso = true)` — Aplica o estado visual (válido/inválido) em um .campo.

### `frontend/js/viagem-agenda.js`  <small>(188 linhas)</small>

Aba Agenda: três visões (dia, semana, linha do tempo), destaque de conflitos, eventos vindos do roteiro (somente leitura aqui) e formulário de compromissos.

**Estrutura**

- **`Agenda`** (objeto/classe de nível superior)
- `eventosDoDia(dataIso)`
- `cartaoEvento(e, mini = false)`
- `desenharAgenda(painel)`
- `visaoDia()`
- `visaoSemana()`
- `visaoLinha()`
- `clicarEvento(chave)`
- `abrirFormularioCompromisso({ compromisso = null, data = null } = {})`

**Endpoints que usa:** `calendario` → GET /api/viagens/:id/calendario; `criarCompromisso` → POST /api/viagens/:id/compromissos; `editarCompromisso` → PUT /api/compromissos/:id; `excluirCompromisso` → DELETE /api/compromissos/:id

### `frontend/js/viagem-checklist.js`  <small>(103 linhas)</small>

Aba Checklist: progresso, sugestões, adição, marcação (salva na hora, com reversão se falhar), remoção e reuso da lista de outra viagem.

**Estrutura**

- `desenharChecklist(painel, c)`
- `importarLista(painel)`

**Endpoints que usa:** `adicionarItem` → POST /api/viagens/:id/checklist; `atualizarItem` → PATCH /api/checklist/:id; `checklist` → GET /api/viagens/:id/checklist; `importarChecklist` → ?; `listarViagens` → GET /api/viagens${status ? ; `removerItem` → DELETE /api/checklist/:id; `sugerirChecklist` → POST /api/viagens/:id/checklist/sugestoes

### `frontend/js/viagem-gastos.js`  <small>(150 linhas)</small>

Aba Gastos: KPIs, barra de uso do orçamento, gráfico de rosca, planejado × gasto, quem pagou, lista de despesas e os formulários de despesa e de orçamento.

**Estrutura**

- `desenharGastos(painel, f)`
- `abrirFormularioDespesa(f, painel, despesa = null)`
- `abrirFormularioOrcamento(f, painel)`

**Endpoints que usa:** `definirOrcamento` → PUT /api/viagens/:id/orcamento; `editarDespesa` → PUT /api/despesas/:id; `excluirDespesa` → DELETE /api/despesas/:id; `financas` → GET /api/viagens/:id/financas; `registrarDespesa` → POST /api/viagens/:id/despesas

### `frontend/js/viagem-grupo.js`  <small>(153 linhas)</small>

Aba Grupo: participantes, convite por e-mail, mudança de papel, remover/sair e **decisões do grupo** (sugerir, votar, aprovar com escolha do dia, rejeitar).

**Estrutura**

- `desenharGrupo(painel, g, s)`
- `cartaoSugestao(s, podeDecidir)`
- `decidirSugestao(id, decisao)`
- `addDias(iso, n)`

**Endpoints que usa:** `alterarPapel` → ?; `convidar` → POST /api/viagens/:id/participantes; `decidir` → POST /api/sugestoes/:id/decisao; `participantes` → GET /api/viagens/:id/participantes; `removerParticipante` → DELETE /api/viagens/:id/participantes/:id; `sugerir` → POST /api/viagens/:id/sugestoes; `sugestoes` → GET /api/viagens/:id/sugestoes; `votar` → POST /api/sugestoes/:id/voto

### `frontend/js/viagem-mapa.js`  <small>(135 linhas)</small>

Aba Mapa: marcadores numerados por dia, trajetos, distâncias por dia, **medição entre dois pontos**, mostrar/ocultar dias, clique no mapa para criar atividade e lugares próximos.

**Estrutura**

- `montarMapaViagem(painel, dados)`
- `medir(ponto)`

**Endpoints que usa:** `lugaresMapa` → GET /api/mapa/lugares; `mapaViagem` → GET /api/viagens/:id/mapa; `proximidades` → GET /api/lugares/:id/proximidades?raio_km=:id

### `frontend/js/viagem-roteiro.js`  <small>(335 linhas)</small>

Aba Roteiro: seletor de versões (ativar, duplicar, excluir, nova em branco), gerador do Vai (interesses, ritmo, orçamento, refeições), atividades por dia com mover/editar/excluir, formulário de atividade e o **mini-mapa para marcar o local** (`seletorLocalNoMapa`).

**Estrutura**

- **`Roteiro`** (objeto/classe de nível superior)
- **`FONTES_ATIVIDADE`** (objeto/classe de nível superior)
- `dataDoDia(numero)`
- `desenharRoteiro(painel)`
- `cartaoAtividade(a, indice, total, dia, dias)`
- `moverAtividade(id, passo, painel)` — Sobe/desce dentro do dia; nas pontas, passa para o dia anterior/seguinte.
- `criarRoteiroManual()`
- `abrirGeradorRoteiro()` — ------------------------------ geração ---------------------------------
- `seletorLocalNoMapa(container, form, { latitude, longitude } = {})` — Mini-mapa: um clique define latitude/longitude nos campos ocultos do formulário.
- `abrirFormularioAtividade({ atividade = null, dia = 1, latitude = null, longitude = null, lugarId = null } = {})` — --------------------------- atividade (form) ----------------------------

**Endpoints que usa:** `adicionarAtividade` → POST /api/roteiros/:id/atividades; `ativarRoteiro` → POST /api/roteiros/:id/ativar; `criarRoteiro` → POST /api/viagens/:id/roteiros; `duplicarRoteiro` → POST /api/roteiros/:id/duplicar; `editarAtividade` → PATCH /api/atividades/:id; `excluirAtividade` → DELETE /api/atividades/:id; `excluirRoteiro` → DELETE /api/roteiros/:id; `gerarRoteiro` → POST /api/viagens/:id/roteiros/gerar; `opcoesPreferencias` → GET /api/preferencias/opcoes; `perfil` → GET /api/usuarios/eu; `reorganizarRoteiro` → PUT /api/roteiros/:id/ordem; `roteiro` → GET /api/roteiros/:id; `roteiros` → GET /api/viagens/:id/roteiros

### `frontend/js/viagem.js`  <small>(191 linhas)</small>

Núcleo da página da viagem: objeto `Painel` (carrega a viagem, monta a capa e as abas, controla permissões de edição, editar e excluir) e a aba **Resumo** (contagem regressiva, KPIs, próximos compromissos, memórias). Cada aba é registrada com `Painel.registrar`.

**Estrutura**

- **`Painel`** (objeto/classe de nível superior)

**Endpoints que usa:** `calendario` → GET /api/viagens/:id/calendario; `diarioDaViagem` → GET /api/viagens/:id/diario; `excluirViagem` → DELETE /api/viagens/:id; `viagem` → GET /api/viagens/:id

### `frontend/js/viagens.js`  <small>(103 linhas)</small>

Lista de viagens (cartões, contagem por status, estado vazio) e **convites pendentes** com aceitar/recusar.

**Estrutura**

- `criar(lugarId)`
- `carregar()`
- `cartaoViagem(v)`
- `carregarConvites()`

**Endpoints que usa:** `aceitarConvite` → POST /api/convites/:id/aceitar; `convites` → GET /api/convites; `listarViagens` → GET /api/viagens${status ? ; `recusarConvite` → POST /api/convites/:id/recusar

---

## 13. Ferramentas

### `tools/fotos.py`  <small>(162 linhas)</small>

Linha de comando de curadoria: `sincronizar`, `listar`, `aprovar`, `rejeitar`, `principal` e `fundo`. `gerar_versoes_fundo` recorta e converte a foto escolhida em WebP/JPEG de 960, 1600 e 2400 px e um recorte vertical 9:16 para celulares, e grava `fundo.json` com o crédito.

**Estrutura**

- **Constantes:** `LARGURAS_PAISAGEM`, `LARGURAS_RETRATO`
- **Função `gerar_versoes_fundo(conteudo, pasta, prefixo)`** — Recorta/redimensiona a imagem original. Devolve (fontes, fontes_retrato).
- **Função `comando_sincronizar(args)`**
- **Função `comando_listar(args)`**
- **Função `comando_fundo(args)`**
- **Função `main(argv)`**

**Usa:** `app.py`, `config.py`, `extensions.py`, `models/foto_lugar.py`, `services/fotos_lugar_service.py`  
**Usado por:** `tests/test_funcionalidades.py`

### `tools/gerar_imagens.py`  <small>(151 linhas)</small>

Script original que gerou as ilustrações do app com numpy/Pillow. Não é usado em produção.

**Estrutura**

- **Constantes:** `OUT`
- **Função `fbm(h, w, octaves, base, gain, seed)`**
- **Função `lerp(a, b, t)`**
- **Função `praia_por_do_sol(w, h)`**
- **Função `cartao(nome, cores, seed, textura)`** — Imagem abstrata para os cartões de destino (720x480).

---

## 14. Versão de demonstração sem backend (branch `demo-estatico`)

Não fazem parte da branch principal: são acrescentados ao mesmo `frontend/`.

### `js/demo-dados.js`  <small>(3 linhas)</small>

Catálogo gerado a partir do código real (`seeds.py`, `geo.py`, `checklist_service.py`): lugares, interesses, cidades com coordenadas, faixas de orçamento, listas do checklist e tipos de viagem.

### `js/demo-backend.js`  <small>(926 linhas)</small>

**Servidor de mentira que roda no navegador.** Substitui `window.fetch` para interceptar tudo que vai a `/api/...` e responde com as mesmas regras do backend (validações, match, roteiro por proximidade, finanças, checklist, agenda com conflitos, avaliações, diário, comparador e Vai), guardando os dados em `localStorage`. Assim as telas funcionam sem mudar nenhum outro script. Limites: sem e-mail, fotos reais, upload, convites entre pessoas e integrações externas.

**Rotas simuladas (86)**

| Método | Caminho |
|---|---|
| `POST` | `/api/auth/cadastro` |
| `POST` | `/api/auth/verificar` |
| `POST` | `/api/auth/reenviar-codigo` |
| `POST` | `/api/auth/login` |
| `POST` | `/api/auth/logout` |
| `GET` | `/api/usuarios/eu` |
| `GET` | `/api/preferencias/opcoes` |
| `GET` | `/api/preferencias` |
| `PUT` | `/api/preferencias` |
| `POST` | `/api/preferencias` |
| `GET` | `/api/lugares` |
| `GET` | `/api/lugares/busca` |
| `GET` | `/api/lugares/recomendacoes` |
| `GET` | `/api/lugares/:id` |
| `GET` | `/api/lugares/:id/fotos` |
| `GET` | `/api/favoritos` |
| `POST` | `/api/favoritos` |
| `DELETE` | `/api/favoritos/:id` |
| `GET` | `/api/chat` |
| `POST` | `/api/chat` |
| `GET` | `/api/chat/permissoes` |
| `PUT` | `/api/chat/permissoes` |
| `GET` | `/api/viagens` |
| `POST` | `/api/viagens` |
| `GET` | `/api/viagens/:id` |
| `PUT` | `/api/viagens/:id` |
| `PATCH` | `/api/viagens/:id` |
| `DELETE` | `/api/viagens/:id` |
| `GET` | `/api/viagens/:id/roteiros` |
| `POST` | `/api/viagens/:id/roteiros` |
| `POST` | `/api/viagens/:id/roteiros/gerar` |
| `GET` | `/api/roteiros/:id` |
| `DELETE` | `/api/roteiros/:id` |
| `POST` | `/api/roteiros/:id/duplicar` |
| `POST` | `/api/roteiros/:id/ativar` |
| `PUT` | `/api/roteiros/:id/ordem` |
| `POST` | `/api/roteiros/:id/atividades` |
| `PUT` | `/api/atividades/:id` |
| `PATCH` | `/api/atividades/:id` |
| `DELETE` | `/api/atividades/:id` |
| `GET` | `/api/viagens/:id/financas` |
| `PUT` | `/api/viagens/:id/orcamento` |
| `POST` | `/api/viagens/:id/despesas` |
| `PUT` | `/api/despesas/:id` |
| `PATCH` | `/api/despesas/:id` |
| `DELETE` | `/api/despesas/:id` |
| `GET` | `/api/viagens/:id/checklist` |
| `POST` | `/api/viagens/:id/checklist/sugestoes` |
| `POST` | `/api/viagens/:id/checklist` |
| `POST` | `/api/viagens/:id/checklist/importar` |
| `PATCH` | `/api/checklist/:id` |
| `PUT` | `/api/checklist/:id` |
| `DELETE` | `/api/checklist/:id` |
| `GET` | `/api/viagens/:id/calendario` |
| `POST` | `/api/viagens/:id/compromissos` |
| `PUT` | `/api/compromissos/:id` |
| `PATCH` | `/api/compromissos/:id` |
| `DELETE` | `/api/compromissos/:id` |
| `GET` | `/api/viagens/:id/participantes` |
| `POST` | `/api/viagens/:id/participantes` |
| `GET` | `/api/convites` |
| `GET` | `/api/viagens/:id/sugestoes` |
| `POST` | `/api/viagens/:id/sugestoes` |
| `POST` | `/api/sugestoes/:id/voto` |
| `POST` | `/api/sugestoes/:id/decisao` |
| `GET` | `/api/lugares/:id/avaliacoes` |
| `POST` | `/api/lugares/:id/avaliacoes` |
| `PUT` | `/api/avaliacoes/:id` |
| `POST` | `/api/avaliacoes/:id` |
| `DELETE` | `/api/avaliacoes/:id` |
| `GET` | `/api/comunidade` |
| `GET` | `/api/diario` |
| `POST` | `/api/diario` |
| `GET` | `/api/diario/estatisticas` |
| `PUT` | `/api/diario/:id` |
| `POST` | `/api/diario/:id` |
| `DELETE` | `/api/diario/:id` |
| `GET` | `/api/viagens/:id/diario` |
| `GET` | `/api/vitrine/fundo` |
| `GET` | `/api/mapa/config` |
| `GET` | `/api/mapa/lugares` |
| `GET` | `/api/viagens/:id/mapa` |
| `GET` | `/api/lugares/:id/proximidades` |
| `GET` | `/api/comparador` |
| `GET` | `/api/saude` |
| `GET` | `/api/relatorios/destinos` |

**Funções internas:** `calcMatch`, `lugarDict`, `viagemDict`, `viagemDoUsuario`, `validarViagem`, `aplicarCoordenadas`, `resumoViagem`, `novaVersao`, `roteiroDoUsuario`, `atividadeDoUsuario`, `validarAtividade`, `gerarPlano`, `resumoFinanceiro`, `validarDespesa`, `checklistResp`, `sugerirItens`, `itemDoUsuario`, `calendario`, `validarComp`, `avalDict`, `diarioDict`, `sugDict`, `responderVai`, `corpoDe`, `atender`

### `.htaccess`  <small>(24 linhas)</small>

Política de segurança própria da pasta no servidor da Hostinger (permite estilos embutidos e tiles do OpenStreetMap) e bloqueio de arquivos ocultos como `.git`.

---

## Arquivos sem capítulo próprio

- `frontend/vendor/leaflet/` — biblioteca Leaflet 1.9.4 (mapas), copiada do pacote oficial; não é código do projeto.
- `frontend/assets/` — ilustrações SVG dos cartões por categoria (`card-*.svg`) e a imagem original de fundo (`praia.jpg`).
