# Viajaí ✈️

Plataforma de viagens que acompanha o usuário da **descoberta** do destino ao **planejamento**,
à **realização** e ao **registro** da viagem. O usuário cria a conta (com verificação de e-mail
por código), informa interesses, orçamento e localização e recebe destinos, restaurantes e
experiências ordenados por um **percentual de compatibilidade (match)**. A partir daí planeja
viagens (sozinho ou em grupo), gera roteiros com o assistente **Vai**, controla gastos, organiza a
agenda e a mala, vê tudo no mapa, compara destinos, avalia lugares e mantém um diário.

Backend em **Flask + SQLAlchemy** organizado em camadas (Controllers → Services → Models /
Repositories) e frontend em **HTML, CSS e JavaScript puro** consumindo a API REST.

---

## Funcionalidades

### Base (versão anterior — preservadas)

1. **Cadastrar usuário** com validação no frontend e no backend.
2. **Verificar código de e-mail** (6 dígitos, validade de 15 minutos).
3. **Reenviar código de verificação**.
4. **Login e logout** com hash de senha e token de sessão.
5. **Perfil do usuário logado**.
6. **Interesses e preferências** (N:N), orçamento e cidade.
7. **Listar e buscar destinos** com filtros e ordenações.
8. **Recomendações personalizadas** (motor de match).
9. **Favoritos** (salvar, remover, listar).
10. **Assistente Vai** com histórico persistido (Gemini + motor local de reserva).
11. **Relatório de destinos** (`GET /api/relatorios/destinos`) com Stored Procedure no MySQL.

### Expansão — 12 novas funcionalidades

| # | Funcionalidade | Onde fica | Destaques |
|---|---|---|---|
| 1 | **Planejador de viagens** | `viagens.html`, `viagem.html` | Destino do catálogo ou livre (geocodificado), datas, viajantes, tipo, orçamento, observações e preferências; filtros Futuras / Em andamento / Concluídas; editar e excluir (com cascata). |
| 2 | **Roteiros inteligentes com o Vai** | aba **Roteiro** | Gera atividades por dia com lugares **reais** (catálogo + OpenStreetMap), agrupadas por proximidade (vizinho mais próximo); respeita interesses, orçamento, ritmo e duração; horários marcados como *sugeridos*; funcionamento só quando vem do OSM; versões (gerar, duplicar, ativar, excluir); editar, excluir, reordenar e mover entre dias; atividades manuais com ponto no mapa. Com Gemini, a IA só escolhe itens da lista de candidatos — o resto é descartado. |
| 3 | **Planejamento financeiro** | aba **Gastos** | Orçamento total e por categoria, despesas (hospedagem, alimentação, transporte, passeios, outros), saldo, gasto por pessoa/dia, quem pagou, gráfico de rosca e barras planejado × gasto, alertas a 80% e ao ultrapassar. Valores guardados em centavos (sem erro de arredondamento). |
| 4 | **Mapa interativo** | aba **Mapa**, página do lugar | Leaflet 1.9.4 (servido localmente) + tiles do OpenStreetMap com atribuição; destino, atividades numeradas por dia, compromissos, trajetos por dia, distâncias **em linha reta** (Haversine, rotuladas assim), medição entre dois pontos, lugares e estabelecimentos próximos, clique no mapa para criar atividade. |
| 5 | **Comparador de destinos** | `comparar.html` | Até 3 destinos do catálogo: preço, nota do catálogo, média da comunidade, atrações por perto (catálogo e OSM), características, clima (Open-Meteo, quando disponível), distância, match e interesses compatíveis; destaca a vantagem em cada critério. |
| 6 | **Checklist inteligente** | aba **Checklist** | Sugestões por destino, duração, tipo de viagem e interesses; categorias; itens próprios; marcar salva na hora; percentual; reusar a lista de outra viagem. |
| 7 | **Viagens em grupo** | aba **Grupo**, convites em `viagens.html` | Convite por e-mail (conta verificada), aceitar/recusar, papéis **editor** e **viajante**, remover participante ou sair, sugestões com votação 👍/👎 e decisão (aprovar vira atividade do roteiro). Quem não participa recebe 404. |
| 8 | **Avaliações e experiências** | `lugar.html`, `comunidade.html` | Nota 1–5, título, comentário, data da visita, até 6 fotos; média e distribuição só da comunidade (separadas da nota do catálogo); uma avaliação por pessoa e lugar; editar/excluir as próprias; selo **"viagem verificada"** quando o autor tem viagem concluída no Viajaí que passou pelo lugar; feed da comunidade. |
| 9 | **Calendário da viagem** | aba **Agenda** | Compromissos (reserva, passeio, transporte, hospedagem, refeição) com data, hora, duração, local e observações; visões **Dia**, **Semana** e **Linha do tempo**; atividades com horário do roteiro principal entram automaticamente; detecção de conflitos. |
| 10 | **Histórico e diário** | `diario.html` | Memórias com relato, fotos, local, lugar do catálogo, viagem, nota pessoal e visibilidade (só eu / participantes / comunidade); linha do tempo por ano; estatísticas (viagens, dias, destinos, estados/países, fotos, nota média, estilo favorito). |
| 11 | **Fotografias reais dos lugares** | cartões, página do lugar, comparador | Tabela `fotos_lugar` com autor, licença e origem; sincronização pelo backend (Wikimedia sem chave; Pexels/Unsplash com chave); só fotos **verificadas** aparecem; galeria com miniaturas e lightbox (teclado e toque), lazy loading e fallback para ilustração **rotulada como ilustração**. |
| 12 | **Fundo profissional na tela inicial** | `index.html` | Camada de fotografia real (srcset responsivo, enquadramento vertical opcional para celular), gradientes para contraste, aparecimento suave, crédito da foto, layout ampliado em tablet/desktop; mantém marca, aviso, chips, título e botões; fallback para o fundo anterior se a foto não carregar. |

### Integração com o Vai (assistente existente, expandido)

- **Permissões** (`🔒` no chat): favoritos, viagens/roteiros/agenda, orçamentos/gastos e diário —
  todas começam **desligadas**. Escolher uma viagem no seletor do chat autoriza os dados só dela.
- O Vai responde sobre a próxima viagem, gastos, agenda/conflitos e o que falta na mala, e devolve
  **ações** (botões): criar viagem para um destino citado, gerar roteiro, abrir gastos/agenda/checklist, comparar.
- O prompt do Gemini recebe apenas os dados autorizados e a instrução de não inventar preços,
  horários, disponibilidade ou estabelecimentos. Sem chave, o motor local responde com os mesmos dados.

---

## Tecnologias

| Camada | Tecnologia |
| --- | --- |
| Backend | Python 3.10+, Flask, Flask-SQLAlchemy, Flask-CORS, Pillow (tratamento de uploads) |
| Banco | SQLite (padrão) — compatível com MySQL trocando a `DATABASE_URL` |
| IA | Google Gemini (API REST) com motor local de reserva |
| Mapas | Leaflet 1.9.4 (em `frontend/vendor/leaflet`, licença BSD-2) + OpenStreetMap |
| Dados externos | Wikipédia/Wikimedia Commons, Pexels, Unsplash, Overpass API, Nominatim, Open-Meteo (todos pelo backend) |
| Frontend | HTML5, CSS3 e JavaScript (sem framework, sem build) |

---

## Como executar

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                 # Windows: copy .env.example .env
python run.py
```

Abra **http://localhost:5000**. O banco e a carga inicial são criados automaticamente; bancos de
versões anteriores são atualizados por migrações não destrutivas (veja *Banco de dados*).

> **Código de verificação:** com `EMAIL_MODO=console` (padrão) o código é impresso no terminal e,
> em desenvolvimento, aparece na tela.

### Configurações e credenciais externas

Nenhuma chave vai para o frontend nem para o repositório (`.env` está no `.gitignore`).

| Variável | Para quê | Obrigatória? |
|---|---|---|
| `GEMINI_API_KEY` | Vai com Gemini (chat e roteiros) | Não — sem ela, motor local |
| `INTEGRACOES_EXTERNAS` | `1` liga, `0` desliga todas as chamadas externas | Padrão `1` |
| `HTTP_USER_AGENT` | Identificação exigida por Wikimedia e Nominatim — **coloque um contato real** | Recomendado |
| `FOTOS_SINCRONIZACAO_AUTOMATICA` | Busca fotos da Wikimedia em segundo plano ao iniciar (só lugares sem foto) | Padrão `1` |
| `PEXELS_API_KEY` | Candidatas de foto do Pexels (ficam pendentes de curadoria) | Não |
| `UNSPLASH_ACCESS_KEY` | Candidatas de foto do Unsplash (pendentes de curadoria) | Não |
| `MAPA_TILE_URL` / `MAPA_TILE_ATRIBUICAO` | Provedor de tiles do mapa | Padrão: OpenStreetMap |
| `NOMINATIM_URL`, `OVERPASS_URL`, `OPEN_METEO_URL` | Endpoints (permite usar instâncias próprias) | Padrão: públicos |
| `UPLOAD_TAMANHO_MAXIMO_MB`, `UPLOAD_MAXIMO_FOTOS`, `PASTA_UPLOADS` | Limites e pasta das fotos enviadas | Padrão: 5 MB, 6 fotos, `backend/uploads` |

**Uso responsável dos serviços públicos:** o backend respeita 1 requisição/s no Nominatim, envia
User-Agent identificado, guarda respostas em cache (`cache_externo`, `pontos_interesse`) e trata
falhas sem quebrar a tela. Para produção com tráfego, use um provedor de tiles e de geocodificação
contratado ou próprio (a política dos servidores do OpenStreetMap não permite uso pesado).

### Fotografias reais — curadoria

```bash
python -m tools.fotos sincronizar                    # Wikimedia: grava fotos já verificadas
python -m tools.fotos sincronizar --fonte pexels     # candidatas NÃO verificadas
python -m tools.fotos listar --pendentes
python -m tools.fotos aprovar 12 13                  # depois de conferir que é o lugar
python -m tools.fotos rejeitar 14
python -m tools.fotos principal 12
python -m tools.fotos fundo                          # gera o fundo otimizado da tela inicial
```

**Critério de verificação automática (Wikimedia):** a imagem principal do artigo da Wikipédia
só é aceita se as coordenadas do artigo estiverem a até `raio_km` das coordenadas do lugar; fotos
georreferenciadas do Commons precisam estar no raio **e** ter o nome do lugar (ou um termo curado
em `REFERENCIAS_FOTOS`, `backend/seeds.py`) no título. Só licenças livres (CC0, CC BY, CC BY-SA,
domínio público) entram, e autor/licença/origem são exibidos em cada foto. Buscas por texto
(Pexels/Unsplash) nunca são marcadas como verificadas automaticamente. Lugares sem foto
confirmada mostram a ilustração da categoria **com o aviso de que é uma ilustração**.

`tools.fotos fundo` baixa a melhor paisagem verificada (ou `--foto ID`), gera WebP/JPEG em 960,
1600 e 2400 px e um recorte vertical para celulares em `frontend/assets/fundo/`, com
`fundo.json` contendo o crédito. Sem esses arquivos, a tela inicial usa as miniaturas responsivas
do Commons; sem nenhuma foto, mantém o fundo anterior.

### Usando MySQL (opcional)

```
DATABASE_URL=mysql+pymysql://usuario:senha@localhost:3306/viajai
```

Instale o `PyMySQL` e, para a Stored Procedure do ranking:
`mysql -u usuario -p viajai < backend/sql/procedures_mysql.sql`.

---

## Estrutura do projeto

```
viajai/
├── run.py · requirements.txt · .env.example
├── backend/
│   ├── app.py                 # fábrica, blueprints, erros, cabeçalhos de segurança (CSP), FK no SQLite
│   ├── config.py              # tudo via variáveis de ambiente
│   ├── migracoes.py           # migrações versionadas e não destrutivas
│   ├── seeds.py               # interesses, 20 lugares e referências para as fotos
│   ├── controllers/           # uma classe por recurso
│   │   ├── auth · usuario · preferencia · lugar · favorito · chat · relatorio      (originais)
│   │   └── viagem · roteiro · despesa · checklist · calendario · grupo ·
│   │       avaliacao · diario · foto · mapa · comparador                            (novos)
│   ├── services/              # casos de uso (uma classe por caso de uso)
│   │   ├── ... originais (cadastrar_usuario_service.py etc.)
│   │   ├── autorizacao_viagem_service.py   # leitura / edição / proprietário
│   │   ├── viagens_service.py · roteiros_service.py · roteiro_inteligente_service.py
│   │   ├── financas_service.py · checklist_service.py · calendario_service.py · grupo_service.py
│   │   ├── avaliacoes_service.py · diario_service.py · fotos_lugar_service.py
│   │   ├── mapa_service.py · comparador_service.py · assistente_service.py
│   │   └── integracoes/       # cliente_http (cache, User-Agent, limite por host), geocodificação,
│   │                          # pontos de interesse (Overpass), clima, fotos Wikimedia/Pexels/Unsplash
│   ├── models/                # entidades + CRUD convencional (ModeloBase)
│   ├── repositories/          # consultas especiais (inclui viagem_repository.py)
│   ├── utils/                 # validações, erros, autenticação, geo, arquivos (upload/URL assinada),
│   │                          # limite_requisicoes, requisicao
│   ├── sql/procedures_mysql.sql
│   └── tests/                 # test_regras.py (regras) e test_funcionalidades.py (API completa)
├── frontend/
│   ├── index.html             # boas-vindas com fotografia real de fundo
│   ├── cadastro · login · interesses · app (início/explorar/salvos/perfil) · chat
│   ├── viagens.html · viagem.html (abas) · lugar.html · comparar.html · diario.html · comunidade.html
│   ├── css/estilos.css        # folha única (tokens da identidade original + componentes novos)
│   ├── js/api.js · ui.js · formulario-viagem.js · viagem*.js · lugar.js · comparar.js · diario.js ...
│   ├── vendor/leaflet/        # Leaflet 1.9.4 (sem CDN — compatível com a CSP)
│   └── assets/                # ilustrações e (opcional) fundo/ gerado pelo tools/fotos.py
└── tools/
    ├── fotos.py               # curadoria das fotos e geração do fundo
    └── gerar_imagens.py       # gerador das ilustrações originais
```

---

## Arquitetura

**Controller → Service → Model / Repository** (mantida). Controllers só leem a requisição e
devolvem a resposta; Services validam e aplicam regras; Models fazem o CRUD simples; Repositories
concentram consultas especiais. Os novos módulos de Service agrupam as classes de um mesmo recurso
(`viagens_service.py` contém `CriarViagemService`, `EditarViagemService`...), cada uma com um caso
de uso e um método `executar`.

**Autorização por viagem** (`AutorizacaoViagemService`): `leitura` (organizador + participantes
que aceitaram), `edicao` (organizador + editores) e `proprietario`. Quem não participa recebe 404;
quem participa sem nível suficiente, 403. Todo recurso filho (despesa, item, compromisso,
atividade, sugestão) é checado pela viagem a que pertence.

---

## Banco de dados

### Novas tabelas e relacionamentos

| Tabela | Relacionamentos |
|---|---|
| `viagens` | N:1 `usuarios` (proprietário), N:1 `lugares` (destino do catálogo, `SET NULL`) |
| `participantes_viagem` | N:1 `viagens` (`CASCADE`), N:1 `usuarios`; único (viagem, usuário) |
| `roteiros` | N:1 `viagens` (`CASCADE`); único (viagem, versão) |
| `atividades_roteiro` | N:1 `roteiros` (`CASCADE`), N:1 `lugares`, N:1 `pontos_interesse` (`SET NULL`) |
| `despesas` | N:1 `viagens` (`CASCADE`), N:1 `usuarios` (pagou / criou); valor ≥ 0 em centavos |
| `planejamento_orcamento` | N:1 `viagens`; único (viagem, categoria) |
| `itens_checklist` | N:1 `viagens` (`CASCADE`) |
| `compromissos` | N:1 `viagens` (`CASCADE`) |
| `sugestoes_viagem` / `votos_sugestao` | N:1 `viagens`; votos únicos por (sugestão, usuário) |
| `avaliacoes` / `fotos_avaliacao` | N:1 `usuarios`, N:1 `lugares`; **única por (usuário, lugar)**; nota 1–5 |
| `registros_diario` / `fotos_diario` | N:1 `usuarios`, N:1 `viagens`/`lugares` (`SET NULL`) |
| `fotos_lugar` | N:1 `lugares` (`CASCADE`); única (lugar, URL) |
| `pontos_interesse` | cache persistente do OpenStreetMap; único (tipo OSM, id OSM) |
| `cache_externo` | respostas de integrações com expiração |
| `permissoes_assistente` | 1:1 `usuarios` — consentimentos do Vai |
| `migracoes_aplicadas` | controle de migrações |

### Migrações seguras

`backend/migracoes.py` executa cada migração uma única vez (registrada em
`migracoes_aplicadas`) e só **cria** o que falta — nenhuma tabela, coluna ou dado existente é
alterado ou removido. As tabelas antigas não foram modificadas. No SQLite, `PRAGMA foreign_keys=ON`
é ativado para que as regras `ON DELETE` valham também no banco.

---

## Segurança

- Todas as rotas novas exigem login (exceto leitura pública de lugares, fotos, avaliações,
  comunidade, comparador e mapa geral); dados de viagem isolados por participação.
- Validação de todas as entradas no backend (datas, horários, valores, coordenadas, escolhas, tamanhos).
- Uploads: só JPEG/PNG/WebP conferidos pela assinatura binária, recodificados com Pillow (remove
  EXIF/GPS, limita a 1920 px), nomes aleatórios, fora da pasta pública, servidos por **URL
  assinada com validade** (HMAC com `SECRET_KEY`); limite de 5 MB por foto e corpo máximo da requisição.
- Limite de requisições em login, cadastro, verificação, chat, geração de roteiro, convites,
  avaliações, diário, comparador e proximidades.
- Cabeçalhos: `Content-Security-Policy` (scripts só da própria origem — os `onclick` inline foram
  removidos), `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`.
- Conteúdo de usuários e de fontes externas é escapado antes de ir para o HTML; links externos
  só `http(s)`.
- Chaves (Gemini, Pexels, Unsplash) só no backend.

---

## Endpoints da API

### Originais

| Método | Rota | Descrição |
| --- | --- | --- |
| POST | `/api/auth/cadastro` · `/verificar` · `/reenviar-codigo` · `/login` · `/logout` | Autenticação |
| GET | `/api/usuarios/eu` | Perfil |
| GET/PUT | `/api/preferencias` · GET `/api/preferencias/opcoes` | Preferências |
| GET | `/api/lugares` · `/busca` · `/recomendacoes` · `/<id>` (agora com `fotos`) | Lugares |
| GET/POST/DELETE | `/api/favoritos` · `/api/favoritos/<id>` | Favoritos |
| GET/POST | `/api/chat` (POST aceita `viagem_id`; resposta traz `acoes`) | Vai |
| GET | `/api/relatorios/destinos` · `/api/saude` | Relatório e saúde |

### Novos

| Método | Rota | Descrição |
| --- | --- | --- |
| GET/PUT | `/api/chat/permissoes` | Consentimentos do Vai |
| GET/POST | `/api/viagens` (`?status=futura\|em_andamento\|concluida`) | Listar / criar viagem |
| GET/PUT/DELETE | `/api/viagens/<id>` | Detalhar (com resumo e permissões) / editar / excluir |
| GET/POST | `/api/viagens/<id>/roteiros` | Versões / nova versão em branco |
| POST | `/api/viagens/<id>/roteiros/gerar` | Roteiro inteligente (nova versão) |
| GET/DELETE | `/api/roteiros/<id>` | Ver / excluir versão |
| POST | `/api/roteiros/<id>/duplicar` · `/ativar` | Duplicar / tornar principal |
| PUT | `/api/roteiros/<id>/ordem` | Reorganizar (dia e ordem em lote) |
| POST | `/api/roteiros/<id>/atividades` | Adicionar atividade |
| PATCH/DELETE | `/api/atividades/<id>` | Editar / excluir atividade |
| GET | `/api/viagens/<id>/financas` | Resumo financeiro |
| PUT | `/api/viagens/<id>/orcamento` | Orçamento total e por categoria |
| POST | `/api/viagens/<id>/despesas` · PUT/DELETE `/api/despesas/<id>` | Despesas |
| GET/POST | `/api/viagens/<id>/checklist` | Listar / adicionar item |
| POST | `/api/viagens/<id>/checklist/sugestoes` · `/importar` | Sugerir / reusar lista |
| PATCH/DELETE | `/api/checklist/<id>` | Marcar, editar / remover |
| GET | `/api/viagens/<id>/calendario` | Agenda unificada + conflitos |
| POST | `/api/viagens/<id>/compromissos` · PUT/DELETE `/api/compromissos/<id>` | Compromissos |
| GET/POST | `/api/viagens/<id>/participantes` | Participantes / convidar |
| PATCH/DELETE | `/api/viagens/<id>/participantes/<pid>` | Mudar papel / remover ou sair |
| GET | `/api/convites` · POST `/api/convites/<id>/aceitar` · `/recusar` | Convites |
| GET/POST | `/api/viagens/<id>/sugestoes` | Sugestões do grupo |
| POST | `/api/sugestoes/<id>/voto` · `/decisao` | Votar / aprovar ou rejeitar |
| GET/POST | `/api/lugares/<id>/avaliacoes` (POST multipart com `fotos`) | Avaliações |
| PUT/DELETE | `/api/avaliacoes/<id>` · DELETE `/api/avaliacoes/<id>/fotos/<fid>` | Editar / excluir |
| GET | `/api/comunidade` | Feed da comunidade |
| GET/POST | `/api/diario` · GET `/api/diario/estatisticas` | Diário |
| PUT/DELETE | `/api/diario/<id>` · DELETE `/api/diario/<id>/fotos/<fid>` | Editar / excluir |
| GET | `/api/viagens/<id>/diario` | Memórias compartilhadas da viagem |
| GET | `/api/lugares/<id>/fotos` · `/api/vitrine/fundo` | Fotos verificadas / fundo inicial |
| GET | `/api/arquivos/<pasta>/<nome>?exp=&sig=` | Fotos enviadas (URL assinada) |
| GET | `/api/mapa/config` · `/api/mapa/lugares` · `/api/viagens/<id>/mapa` · `/api/lugares/<id>/proximidades` | Mapa |
| GET | `/api/comparador?ids=1,2,3` | Comparar destinos |

---

## Testes

```bash
python -m backend.tests.test_regras                          # regras de negócio (original)
python -m unittest backend.tests.test_funcionalidades -v     # 23 testes de integração da API
```

`test_funcionalidades` sobe o app com um SQLite temporário e as integrações externas desligadas e
cobre: compatibilidade com o fluxo original, CRUD e validações de viagens, convites/papéis e
isolamento entre usuários, geração de roteiro só com lugares reais (inclusive Gemini simulado
tentando inventar um lugar), funcionamento do OSM, versões e reorganização, finanças e alertas,
checklist e reuso, agenda e conflitos, avaliações (duplicidade, upload, URL assinada, remoção de
EXIF/GPS), diário e visibilidade, fotos (respostas da Wikimedia **simuladas**, licenças, coordenadas
divergentes, curadoria), mapa, comparador, permissões do Vai, limite de requisições, envio grande
demais e migração de um banco antigo sem perda de dados.
