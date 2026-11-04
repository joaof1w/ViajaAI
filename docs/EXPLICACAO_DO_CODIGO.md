# Viajaí — guia do código, arquivo por arquivo

Este guia explica **o que cada arquivo faz** e como as partes se conectam. Marcamos com 🆕 o que foi criado na expansão (as 12 funcionalidades) e com ✏️ o que já existia e foi alterado. Sem marca = já existia e não mudou.

## 1. Visão geral em 1 minuto

O Viajaí tem duas metades que conversam por uma API REST (JSON):

```
Navegador (frontend/)  ──fetch /api/...──▶  Flask (backend/)  ──▶  Banco SQLite (ou MySQL)
 HTML + CSS + JS puro                        Controllers → Services → Models/Repositories
                                                  │
                                                  └──▶ Serviços externos (Gemini, Wikimedia, OpenStreetMap...)
```

**O caminho de uma requisição** (exemplo: o usuário clica em "Adicionar despesa"):

1. `frontend/js/viagem-gastos.js` chama `Api.registrarDespesa(...)` (definido em `js/api.js`).
2. `api.js` faz `POST /api/viagens/7/despesas` com o token no cabeçalho `Authorization`.
3. O **Controller** (`controllers/despesa_controller.py`) recebe, confere o login (`@login_obrigatorio`) e chama o Service.
4. O **Service** (`services/financas_service.py`) valida os dados, checa se o usuário pode editar essa viagem (`autorizacao_viagem_service.py`), grava no banco e devolve o resumo.
5. O **Model** (`models/despesa.py`) é a tabela; o `ModeloBase` (`models/base.py`) faz o `salvar()`.
6. O Controller devolve JSON; o JS redesenha a tela.

**Regra de ouro da arquitetura:** Controller não tem regra de negócio; Service tem uma regra por classe; Model só descreve a tabela e o CRUD simples; Repository só guarda consultas SQL especiais.

---

## 2. Raiz do projeto

| Arquivo | O que faz |
|---|---|
| `run.py` | Ponto de entrada em desenvolvimento: `python run.py` cria o app e sobe o servidor na porta 5000. |
| 🆕 `wsgi.py` | Ponto de entrada em produção: expõe o objeto `app` para servidores como gunicorn e PythonAnywhere. |
| 🆕 `Procfile` | Diz à hospedagem (Render/Heroku) como iniciar: `gunicorn wsgi:app`. |
| 🆕 `render.yaml` | Receita pronta para publicar no Render (plano gratuito). |
| ✏️ `requirements.txt` | Dependências Python (Flask, SQLAlchemy, requests, **Pillow** e **gunicorn** foram acrescentados). |
| ✏️ `.env.example` | Modelo das variáveis de ambiente (chaves, banco, e-mail, integrações). Copie para `.env`. |
| ✏️ `.gitignore` | O que não vai para o Git (`.env`, banco `.db`, uploads, trava de inicialização). |
| ✏️ `README.md` | Documentação geral: funcionalidades, tabelas, endpoints, testes. |
| 🆕 `DEPLOY.md` | Passo a passo para publicar de graça. |
| 🆕 `docs/EXPLICACAO_DO_CODIGO.md` | Este arquivo. |

---

## 3. Backend (`backend/`)

### 3.1 Núcleo

| Arquivo | O que faz |
|---|---|
| ✏️ `app.py` | **Fábrica da aplicação** (`create_app`). Registra os Controllers, os tratadores de erro (devolvem JSON), os cabeçalhos de segurança (CSP etc.), serve o frontend, cria as tabelas, roda as migrações e a carga inicial. Também ativa as chaves estrangeiras no SQLite, impede subir em produção com a chave secreta padrão e usa um *bloqueio entre processos* para que vários workers não criem as tabelas ao mesmo tempo. |
| ✏️ `config.py` | Lê **todas** as configurações do ambiente (`.env`): banco, Gemini, e-mail, limites de upload, URLs das integrações, chaves Pexels/Unsplash. Nada sensível fica no código. |
| `extensions.py` | Objetos compartilhados (`db` do SQLAlchemy e `cors`) para evitar import circular. |
| 🆕 `migracoes.py` | Migrações **não destrutivas**: cada uma roda uma vez e fica registrada. Só cria tabelas novas; nunca altera ou apaga dados antigos. |
| ✏️ `seeds.py` | Carga inicial do banco: 6 interesses e 20 lugares. 🆕 Também guarda as **referências para as fotos** de cada lugar (título do artigo na Wikipédia, palavras-chave, raio de conferência) e a lista de lugares candidatos ao fundo da tela inicial. |
| `sql/procedures_mysql.sql` | Stored Procedure opcional do ranking (só usada com MySQL). |

### 3.2 Controllers (`controllers/`) — a "porta de entrada" HTTP

Cada classe define as rotas (`registrar`) e converte requisição → chamada de Service → resposta JSON.

| Arquivo | Rotas / responsabilidade |
|---|---|
| `auth_controller.py` ✏️ | Cadastro, verificação do código, reenvio, login e logout. Agora com limite de tentativas por IP. |
| `usuario_controller.py` | `GET /api/usuarios/eu` (perfil). |
| `preferencia_controller.py` | Interesses, orçamento e cidade do usuário. |
| `lugar_controller.py` | Listar, buscar, recomendar e detalhar lugares. |
| `favorito_controller.py` | Salvar, remover e listar favoritos. |
| `chat_controller.py` ✏️ | Conversa com o Vai. 🆕 Aceita `viagem_id` (viagem em foco) e tem as rotas de **permissões do Vai**. |
| `relatorio_controller.py` | Ranking de destinos e estatísticas. |
| 🆕 `viagem_controller.py` | CRUD de viagens (`/api/viagens`). |
| 🆕 `roteiro_controller.py` | Versões do roteiro, geração pelo Vai, atividades (criar, editar, excluir, reordenar). |
| 🆕 `despesa_controller.py` | Resumo financeiro, orçamento e despesas. |
| 🆕 `checklist_controller.py` | Itens da mala, sugestões e importação de lista. |
| 🆕 `calendario_controller.py` | Agenda unificada e compromissos. |
| 🆕 `grupo_controller.py` | Participantes, convites, papéis e sugestões com votação. |
| 🆕 `avaliacao_controller.py` | Avaliações dos lugares (aceita fotos) e feed da comunidade. |
| 🆕 `diario_controller.py` | Diário de viagens e estatísticas. |
| 🆕 `foto_controller.py` | Fotos reais dos lugares, fundo da tela inicial e **entrega das fotos enviadas** (só com URL assinada). |
| 🆕 `mapa_controller.py` | Configuração do mapa, lugares, mapa da viagem e proximidades. |
| 🆕 `comparador_controller.py` | Comparar 2 a 3 destinos. |
| ✏️ `__init__.py` | Lista `CONTROLLERS` — é aqui que um Controller novo é "ligado" ao app. |

### 3.3 Services (`services/`) — as regras de negócio

**Já existiam** (um caso de uso por arquivo): `cadastrar_usuario`, `verificar_codigo`, `reenviar_codigo`, `autenticar_usuario`, `encerrar_sessao`, `obter_perfil`, `listar_interesses`, `salvar_preferencias`, `listar_lugares`, `buscar_lugares`, `recomendar_lugares`, `obter_lugar` ✏️ (agora devolve as fotos), `calcular_match` (nota de compatibilidade 35–99%), `salvar/listar/remover_favorito`, `listar_historico_chat`, `gerar_relatorio`, `envio_email_service` (SMTP ou console).

**Do assistente (existiam, foram ampliados):**

| Arquivo | O que faz |
|---|---|
| ✏️ `enviar_mensagem_chat_service.py` | Recebe a pergunta, monta o contexto (perfil + só os dados que o usuário autorizou), chama a IA e devolve resposta + botões de ação. |
| ✏️ `gemini_service.py` | Integração com o Google Gemini. Ganhou o modo "resposta em JSON" (para roteiros) e instruções para **não inventar** preços, horários ou lugares. |
| ✏️ `assistente_local_service.py` | Motor de reserva quando não há chave do Gemini. Agora também responde sobre viagens, gastos, agenda e mala. |
| 🆕 `assistente_service.py` | Permissões do Vai (tudo desligado por padrão), montagem do contexto autorizado e detecção de intenções ("criar viagem", "abrir gastos"...). |

**Novos, por funcionalidade:**

| Arquivo | O que faz |
|---|---|
| 🆕 `autorizacao_viagem_service.py` | **O guarda das viagens.** Define 3 níveis: leitura (organizador e participantes), edição (organizador e editores) e proprietário. Quem não participa recebe "não encontrado" (não revela que a viagem existe). Todos os outros services passam por ele. |
| 🆕 `viagens_service.py` | Criar, listar, detalhar, editar e excluir viagens; valida datas e orçamento; define as coordenadas do destino. |
| 🆕 `roteiros_service.py` | Versões de roteiro (criar, duplicar, ativar, excluir) e atividades (validar, editar, reordenar em lote). |
| 🆕 `roteiro_inteligente_service.py` | **Cérebro do roteiro.** Junta candidatos reais (catálogo + OpenStreetMap), pontua por interesses/orçamento, agrupa por proximidade (vizinho mais próximo), distribui as atividades por dia com almoço e jantar e confere horário de funcionamento. Com Gemini, a IA só escolhe entre os candidatos; o que ela inventar é descartado. |
| 🆕 `financas_service.py` | Orçamento total e por categoria, despesas, saldo, gasto por pessoa, alertas (80% e estouro). Valores em **centavos**. |
| 🆕 `checklist_service.py` | Gera sugestões conforme destino, duração, tipo e interesses; adiciona, marca, remove e importa itens. |
| 🆕 `calendario_service.py` | Junta compromissos e atividades do roteiro numa agenda só e detecta conflitos de horário. |
| 🆕 `grupo_service.py` | Convites, aceitar/recusar, papéis, remover/sair, sugestões, votos e decisão (aprovar vira atividade do roteiro). |
| 🆕 `avaliacoes_service.py` | Avaliações (uma por pessoa e lugar), média da comunidade, selo "viagem verificada", feed. Valida e salva as fotos. |
| 🆕 `diario_service.py` | Registros do diário, visibilidade (só eu / participantes / comunidade) e estatísticas de viagem. |
| 🆕 `fotos_lugar_service.py` | Sincroniza fotos reais, curadoria (aprovar, rejeitar, principal) e escolha da foto do fundo inicial. |
| 🆕 `mapa_service.py` | Dados do mapa da viagem, trechos por dia e distâncias em linha reta (nunca inventa rotas). |
| 🆕 `comparador_service.py` | Compara destinos em preço, notas, atrações por perto, clima, distância e compatibilidade, destacando a vantagem de cada um. |

**Integrações externas (`services/integracoes/`)** — cada serviço de fora fica isolado aqui:

| Arquivo | O que faz |
|---|---|
| 🆕 `cliente_http.py` | Cliente HTTP comum: identifica o app (User-Agent), respeita intervalo mínimo por site (Nominatim: 1 req/s), guarda respostas em cache e transforma qualquer falha em "serviço indisponível" sem quebrar a tela. |
| 🆕 `geocodificacao_service.py` | Transforma um destino digitado em coordenadas (Nominatim/OpenStreetMap). |
| 🆕 `pontos_interesse_service.py` | Busca restaurantes, museus, mirantes etc. reais (Overpass/OpenStreetMap) e guarda em cache no banco. |
| 🆕 `clima_service.py` | Previsão dos próximos 7 dias (Open-Meteo). Se falhar, não inventa. |
| 🆕 `fotos_wikimedia_service.py` | Fotos reais da Wikipédia/Commons. Só marca como **verificada** se as coordenadas batem com o lugar e a licença é livre; guarda autor, licença e origem. |
| 🆕 `fotos_pexels_service.py` / `fotos_unsplash_service.py` | Candidatas de foto (precisam de chave). Entram **sempre como não verificadas** até alguém aprovar. |

### 3.4 Models (`models/`) — as tabelas

**Existiam:** `usuario`, `codigo_verificacao`, `interesse`, `preferencia`, `lugar` ✏️ (ganhou fotos, tipo e coordenadas no JSON), `favorito`, `mensagem_chat`, `base` (o mixin `ModeloBase` com `salvar/atualizar/deletar/buscar_por_id`).

| Arquivo 🆕 | Tabela(s) |
|---|---|
| `viagem.py` | `viagens` e `participantes_viagem`; regra de status (futura / em andamento / concluída) e de papel. |
| `roteiro.py` | `roteiros` (versões) e `atividades_roteiro`. |
| `despesa.py` | `despesas` e `planejamento_orcamento`. |
| `checklist.py` | `itens_checklist`. |
| `compromisso.py` | `compromissos` (agenda). |
| `sugestao.py` | `sugestoes_viagem` e `votos_sugestao`. |
| `avaliacao.py` | `avaliacoes` e `fotos_avaliacao`. |
| `diario.py` | `registros_diario` e `fotos_diario`. |
| `foto_lugar.py` | `fotos_lugar` (fonte, autor, licença, verificada, principal). |
| `ponto_interesse.py` | `pontos_interesse` (cache do OpenStreetMap). |
| `cache_externo.py` | `cache_externo` (respostas de integrações com validade). |
| `permissao_assistente.py` | `permissoes_assistente` (consentimentos do Vai). |
| `migracao.py` | `migracoes_aplicadas`. |
| `__init__.py` ✏️ | Importa todos os models (necessário para o banco criar as tabelas). |

### 3.5 Repositories (`repositories/`) — consultas SQL especiais

Existiam: `lugar_repository.py` (busca com filtros e candidatos), `favorito_repository.py`, `relatorio_repository.py`. 🆕 `viagem_repository.py`: viagens do usuário (organizador ou participante), resumo agregado da viagem e a checagem que dá o selo de "viagem verificada".

### 3.6 Utils (`utils/`) — ferramentas de apoio

| Arquivo | O que faz |
|---|---|
| ✏️ `validadores.py` | Validações de e-mail, senha etc.; 🆕 agora também de textos, números, dinheiro (aceita "1.234,56"), datas, horas, coordenadas e escolhas. |
| ✏️ `erros.py` | Exceções de domínio que viram respostas HTTP (404, 422, 409...); 🆕 acesso negado (403), limite excedido (429) e integração indisponível (503). |
| ✏️ `geo.py` | Distância (Haversine) e coordenadas das cidades; corrigido o nome "Rio de Janeiro". |
| ✏️ `datas.py` | Data/hora UTC; 🆕 data de hoje e formatação. |
| `autenticacao.py` | Lê o token do cabeçalho e o decorador `@login_obrigatorio`. |
| 🆕 `arquivos.py` | **Segurança dos uploads:** só aceita JPEG/PNG/WebP (confere o conteúdo, não só a extensão), recodifica com Pillow removendo EXIF/GPS, limita tamanho, grava com nome aleatório e gera/valida **URLs assinadas com validade**. |
| 🆕 `limite_requisicoes.py` | Limita quantas vezes por minuto/hora cada usuário ou IP pode chamar rotas sensíveis. |
| 🆕 `requisicao.py` | Lê o corpo da requisição, seja JSON ou formulário com fotos. |

### 3.7 Testes (`tests/`)

| Arquivo | O que faz |
|---|---|
| `test_regras.py` | Testes originais das regras (validações, match, distância, assistente local). |
| 🆕 `apoio.py` | Infraestrutura dos testes: app com banco temporário, criação de usuários, imagens de teste. |
| 🆕 `test_funcionalidades.py` | 24 testes de integração da API (permissões, uploads, roteiro, finanças, migração de banco antigo etc.). |

---

## 4. Frontend (`frontend/`)

### 4.1 Páginas HTML

| Página | Função |
|---|---|
| ✏️ `index.html` | Boas-vindas, agora com **camada de foto real de fundo** (com reserva se não carregar). |
| `cadastro.html`, `login.html`, `interesses.html` ✏️ | Fluxo de entrada (apenas os `onclick` embutidos foram trocados por scripts, exigência da política de segurança). |
| ✏️ `app.html` | Tela principal: início, explorar, salvos, perfil. 🆕 Atalhos (Viagens, Comparar, Diário, Comunidade), mapa geral e resumo de viagens no perfil. |
| ✏️ `chat.html` | O Vai. 🆕 Seletor de viagem em foco e botão de permissões. |
| 🆕 `viagens.html` | Lista de viagens por status e convites pendentes. |
| 🆕 `viagem.html` | Painel de uma viagem, com abas (Resumo, Roteiro, Agenda, Gastos, Checklist, Mapa, Grupo). |
| 🆕 `lugar.html` | Página do lugar: galeria com ampliação, mapa, avaliações. |
| 🆕 `comparar.html` | Comparador de destinos. |
| 🆕 `diario.html` | Diário e estatísticas. |
| 🆕 `comunidade.html` | Feed de avaliações e relatos públicos. |

### 4.2 JavaScript (`frontend/js/`)

| Arquivo | O que faz |
|---|---|
| ✏️ `api.js` | **Única camada que fala com o backend**: `requisitar()` (token, erros, JSON/FormData) e o objeto `Api` com uma função por endpoint. Também guarda a sessão (`Sessao`). |
| 🆕 `ui.js` | Biblioteca de interface: toasts, janelas (folhas), confirmação, escape de HTML, formatação (moeda, data, km), fotos com carregamento sob demanda e reserva, **galeria/lightbox**, estrelas, gráfico de rosca, navegação inferior e criação de mapas Leaflet. |
| `validacoes.js`, `cadastro.js`, `login.js`, `interesses.js` | Telas de entrada (existiam). |
| ✏️ `app.js` | Tela principal (cartões, busca, favoritos, abas); agora usa fotos reais e abre o mapa geral. |
| ✏️ `chat.js` | Chat do Vai; agora com permissões, viagem em foco e botões de ação. |
| 🆕 `inicio.js` | Carrega a foto de fundo da tela inicial com `srcset` responsivo e crédito. |
| 🆕 `viagens.js` | Lista de viagens e convites. |
| 🆕 `formulario-viagem.js` | Formulário de criar/editar viagem (usado em mais de uma tela). |
| 🆕 `viagem.js` | Núcleo da página da viagem: carrega dados, monta abas (`Painel.registrar`) e o resumo. |
| 🆕 `viagem-roteiro.js` | Aba Roteiro: versões, gerador, atividades, mover/editar/excluir, mini-mapa de local. |
| 🆕 `viagem-agenda.js` | Aba Agenda: visões dia, semana e linha do tempo, conflitos, compromissos. |
| 🆕 `viagem-gastos.js` | Aba Gastos: indicadores, gráfico, alertas, despesas e planejamento. |
| 🆕 `viagem-checklist.js` | Aba Checklist: marcar (salva na hora), sugerir, adicionar, reusar lista. |
| 🆕 `viagem-mapa.js` | Aba Mapa: pontos por dia, trajetos, medição de distância, clique para criar atividade. |
| 🆕 `viagem-grupo.js` | Aba Grupo: participantes, convites, permissões e votação. |
| 🆕 `lugar.js` | Página do lugar: galeria, mapa e avaliações. |
| 🆕 `comparar.js` | Escolha e comparação de destinos. |
| 🆕 `diario.js` | Diário: linha do tempo, estatísticas e formulário de memória. |
| 🆕 `comunidade.js` | Feed da comunidade. |

### 4.3 Estilo e recursos

| Arquivo | O que faz |
|---|---|
| ✏️ `css/estilos.css` | Folha única de estilos. As cores e fontes originais (laranja Viajaí etc.) foram mantidas como variáveis; 🆕 foram acrescentados os componentes novos e o fundo da tela inicial. |
| 🆕 `vendor/leaflet/` | Biblioteca de mapas Leaflet 1.9.4, servida do próprio projeto (sem CDN). |
| `assets/` | Ilustrações dos cartões e a imagem original de fundo. |

---

## 5. Ferramentas (`tools/`)

| Arquivo | O que faz |
|---|---|
| 🆕 `fotos.py` | Linha de comando: `sincronizar` (busca fotos), `listar`, `aprovar`, `rejeitar`, `principal` e `fundo` (gera as versões otimizadas do fundo da tela inicial). |
| `gerar_imagens.py` | Gerou as ilustrações originais (não é usado em produção). |

---

## 6. A versão de demonstração sem backend (branch `demo-estatico`)

Não faz parte da branch principal. É o mesmo `frontend/` com dois arquivos a mais:

| Arquivo | O que faz |
|---|---|
| `js/demo-dados.js` | Catálogo (lugares, cidades, listas do checklist), gerado a partir do código real. |
| `js/demo-backend.js` | **Servidor falso no navegador.** Substitui `window.fetch` para interceptar tudo que vai para `/api/...` e responde com as mesmas regras do backend, guardando os dados em `localStorage`. Por isso as telas funcionam sem alterar nenhuma linha dos outros scripts. |
| `.htaccess` | Política de segurança própria da pasta no servidor da Hostinger. |

Limites: dados só no navegador de cada pessoa, sem e-mail, fotos reais, upload, convites entre pessoas ou integrações externas.

---

## 7. Como estender (receita)

Para criar uma funcionalidade nova, siga a ordem:

1. **Model** em `backend/models/` (+ importar em `models/__init__.py` e listar a tabela em `migracoes.py`).
2. **Service** em `backend/services/` (validar, checar permissão, gravar).
3. **Controller** em `backend/controllers/` (rotas) e registrar em `controllers/__init__.py`.
4. **Teste** em `backend/tests/test_funcionalidades.py`.
5. **Frontend**: função em `js/api.js`, depois a tela/aba que a usa.

## 8. Pontos de segurança para lembrar

- Toda viagem passa por `autorizacao_viagem_service.py`; nunca consulte uma viagem direto pelo id.
- Texto vindo de usuários ou de fora **sempre** passa por `escapar()` antes de ir para o HTML.
- Fotos enviadas só saem por URL assinada; fotos reais só aparecem se verificadas.
- Chaves ficam só em `.env`; em produção `FLASK_DEBUG=0` e `SECRET_KEY` própria são obrigatórios.
