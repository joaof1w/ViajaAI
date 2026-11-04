# Viajaí ✈️

Aplicativo de recomendação de viagens: o usuário cria a conta (com verificação de e-mail por
código), informa seus interesses, orçamento e localização, e recebe destinos, restaurantes e
experiências ordenados por um **percentual de compatibilidade (match)**. Também conta com o
**Vai**, assistente de IA integrado para tirar dúvidas sobre a viagem.

Backend em **Flask + SQLAlchemy** organizado em camadas (Controllers → Services → Models /
Repositories) e frontend em **HTML, CSS e JavaScript puro** consumindo a API REST.

---

## Funcionalidades Implementadas

1. **Cadastrar usuário** — nome, e-mail e senha, com validação de formato de e-mail e senha de no mínimo 6 caracteres (validação no frontend e no backend).
2. **Verificar código de e-mail** — código de 6 dígitos com validade de 15 minutos, que ativa a conta e já devolve o token de sessão.
3. **Reenviar código de verificação** — gera um novo código e invalida os anteriores.
4. **Fazer login e logout** — autenticação por e-mail e senha (hash), com bloqueio de contas não verificadas; o logout invalida o token.
5. **Consultar perfil do usuário logado** — dados da conta, preferências e total de lugares salvos.
6. **Salvar interesses e preferências** — interesses (N:N), faixa de orçamento e cidade/estado do usuário.
7. **Listar e buscar destinos com filtros** — por texto, categoria, faixa de preço, estado e nota, com quatro ordenações (nota, mais salvos, preço, nome).
8. **Gerar recomendações personalizadas** — motor de match que cruza interesses, orçamento, avaliação, distância e popularidade.
9. **Salvar, remover e listar favoritos** — o usuário marca lugares no ♥ e os consulta na aba "Salvos".
10. **Conversar com o assistente de IA (Vai)** — chat com histórico persistido, integrado ao Google Gemini e com motor de resposta local de reserva.

**Extra:** relatório de destinos (`GET /api/relatorios/destinos`) com o ranking dos lugares mais
salvos, os interesses mais escolhidos e estatísticas gerais — consultas agregadas isoladas no
`RelatorioRepository`, onde também fica o `CALL` da Stored Procedure quando o banco é MySQL.

---

## Tecnologias

| Camada | Tecnologia |
| --- | --- |
| Backend | Python 3.10+, Flask, Flask-SQLAlchemy, Flask-CORS |
| Banco | SQLite (padrão) — compatível com MySQL trocando a `DATABASE_URL` |
| IA | Google Gemini (API REST) com fallback local |
| Frontend | HTML5, CSS3 e JavaScript (sem framework, sem build) |

---

## Como executar

```bash
# 1. clonar e entrar na pasta
cd viajai

# 2. ambiente virtual (opcional, recomendado)
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. dependências
pip install -r requirements.txt

# 4. variáveis de ambiente
cp .env.example .env             # Windows: copy .env.example .env

# 5. subir a aplicação (cria o banco e a carga inicial automaticamente)
python run.py
```

Abra **http://localhost:5000** no navegador. O próprio Flask serve o frontend, então não é
preciso outro servidor.

> **Código de verificação:** com `EMAIL_MODO=console` (padrão) o código é impresso no terminal
> onde o servidor está rodando e, em modo de desenvolvimento, também aparece na própria tela —
> assim dá para testar o cadastro sem configurar SMTP.

### Ativando a IA (opcional)

Gere uma chave em <https://aistudio.google.com/apikey> e coloque no `.env`:

```
GEMINI_API_KEY=sua-chave-aqui
```

Sem a chave, o chat continua funcionando com o `AssistenteLocalService`, que responde a partir
do perfil e das recomendações do usuário. **A chave nunca vai para o repositório** — o `.env`
está no `.gitignore`.

### Usando MySQL (opcional)

```
DATABASE_URL=mysql+pymysql://usuario:senha@localhost:3306/viajai
```

Instale o `PyMySQL` (linha comentada no `requirements.txt`) e, para habilitar a Stored
Procedure do ranking, execute uma vez:

```bash
mysql -u usuario -p viajai < backend/sql/procedures_mysql.sql
```

O `CALL sp_ranking_destinos(...)` fica encapsulado em `RelatorioRepository` — Controller e
Service nunca executam SQL diretamente.

---

## Estrutura do projeto

```
viajai/
├── run.py                       # ponto de entrada
├── requirements.txt
├── .env.example
├── backend/
│   ├── app.py                   # fábrica da aplicação, blueprints e tratadores de erro
│   ├── config.py                # configuração via variáveis de ambiente
│   ├── extensions.py            # db e cors compartilhados
│   ├── seeds.py                 # carga inicial (interesses + 20 lugares)
│   ├── controllers/             # uma classe por recurso
│   │   ├── auth_controller.py
│   │   ├── usuario_controller.py
│   │   ├── preferencia_controller.py
│   │   ├── lugar_controller.py
│   │   ├── favorito_controller.py
│   │   ├── chat_controller.py
│   │   └── relatorio_controller.py
│   ├── services/                # um Service por caso de uso
│   │   ├── cadastrar_usuario_service.py
│   │   ├── verificar_codigo_service.py
│   │   ├── reenviar_codigo_service.py
│   │   ├── autenticar_usuario_service.py
│   │   ├── encerrar_sessao_service.py
│   │   ├── obter_perfil_service.py
│   │   ├── listar_interesses_service.py
│   │   ├── salvar_preferencias_service.py
│   │   ├── listar_lugares_service.py
│   │   ├── buscar_lugares_service.py
│   │   ├── recomendar_lugares_service.py
│   │   ├── obter_lugar_service.py
│   │   ├── calcular_match_service.py
│   │   ├── salvar_favorito_service.py
│   │   ├── listar_favoritos_service.py
│   │   ├── remover_favorito_service.py
│   │   ├── enviar_mensagem_chat_service.py
│   │   ├── listar_historico_chat_service.py
│   │   ├── gerar_relatorio_service.py
│   │   ├── gemini_service.py           # integração externa (LLM)
│   │   ├── assistente_local_service.py # fallback do chat
│   │   └── envio_email_service.py      # integração externa (SMTP)
│   ├── models/                  # entidades + CRUD convencional
│   │   ├── base.py              # salvar / atualizar / deletar / listar_todos / buscar_por_id
│   │   ├── usuario.py
│   │   ├── codigo_verificacao.py
│   │   ├── interesse.py
│   │   ├── preferencia.py
│   │   ├── lugar.py
│   │   ├── favorito.py
│   │   └── mensagem_chat.py
│   ├── repositories/            # apenas consultas especiais
│   │   ├── lugar_repository.py
│   │   ├── favorito_repository.py
│   │   └── relatorio_repository.py
│   ├── utils/                   # validações, erros, autenticação e distâncias
│   ├── sql/procedures_mysql.sql
│   └── tests/test_regras.py
└── frontend/
    ├── index.html               # boas-vindas (imagem de fundo em tela cheia)
    ├── cadastro.html            # dados + código de verificação
    ├── login.html               # e-mail e senha
    ├── interesses.html          # interesses, orçamento e localização
    ├── app.html                 # início, explorar, salvos e perfil
    ├── chat.html                # assistente Vai
    ├── css/estilos.css
    ├── js/{api,validacoes,cadastro,login,interesses,app,chat}.js
    └── assets/                  # imagem de fundo e ilustrações dos cartões
```

> `tools/gerar_imagens.py` é um utilitário opcional (requer numpy e Pillow) que gerou a imagem
> de fundo da tela de boas-vindas. As imagens já vêm prontas em `frontend/assets/`.

---

## Arquitetura

**Controller → Service → Model / Repository.**

- **Controllers** são classes, uma por recurso. Recebem a requisição HTTP, leem os dados,
  chamam o Service correspondente e devolvem a resposta. Não contêm regra de negócio.
- **Services** têm um caso de uso cada. Validam os dados, aplicam as regras e coordenam Models e
  Repositories. As integrações externas (Gemini e SMTP) estão isoladas em Services próprios.
- **Models** representam as entidades e herdam de `db.Model`. O CRUD convencional
  (`salvar`, `atualizar`, `deletar`, `listar_todos`, `buscar_por_id`) fica na própria Model,
  através do mixin `ModeloBase`.
- **Repositories** existem apenas onde há acesso especial aos dados: filtros combinados,
  joins com contagem de favoritos, candidatos à recomendação, rankings, relatórios e o `CALL`
  da Stored Procedure no MySQL.

### Entidades

`Usuario`, `CodigoVerificacao`, `Interesse`, `Preferencia` (N:N com `Interesse`), `Lugar`,
`Favorito` e `MensagemChat`.

### Como o match é calculado

`CalcularMatchService` parte de uma base e soma/subtrai pontos por: alinhamento com os
interesses escolhidos, nota do lugar, aderência à faixa de orçamento, distância até a cidade do
usuário (fórmula de Haversine) e popularidade entre os usuários do app. O resultado é limitado
entre 35% e 99%.

---

## Endpoints da API

| Método | Rota | Descrição | Autenticação |
| --- | --- | --- | --- |
| POST | `/api/auth/cadastro` | Cadastrar usuário | — |
| POST | `/api/auth/verificar` | Verificar código de e-mail | — |
| POST | `/api/auth/reenviar-codigo` | Reenviar código | — |
| POST | `/api/auth/login` | Entrar | — |
| POST | `/api/auth/logout` | Sair | Bearer |
| GET | `/api/usuarios/eu` | Perfil do usuário logado | Bearer |
| GET | `/api/preferencias/opcoes` | Interesses, faixas de orçamento e cidades | — |
| GET | `/api/preferencias` | Preferências atuais | Bearer |
| PUT | `/api/preferencias` | Salvar preferências | Bearer |
| GET | `/api/lugares` | Listar lugares | opcional |
| GET | `/api/lugares/busca` | Buscar com filtros | opcional |
| GET | `/api/lugares/recomendacoes` | Recomendações personalizadas | Bearer |
| GET | `/api/lugares/<id>` | Detalhes de um lugar | opcional |
| GET | `/api/favoritos` | Listar salvos | Bearer |
| POST | `/api/favoritos` | Salvar lugar | Bearer |
| DELETE | `/api/favoritos/<id>` | Remover dos salvos | Bearer |
| GET | `/api/chat` | Histórico da conversa | Bearer |
| POST | `/api/chat` | Enviar mensagem ao Vai | Bearer |
| GET | `/api/relatorios/destinos` | Ranking e estatísticas | — |
| GET | `/api/saude` | Verificação de disponibilidade | — |

O token é devolvido no login/verificação e enviado no cabeçalho `Authorization: Bearer <token>`.

---

## Fluxo das telas

1. **Boas-vindas** (`index.html`) — imagem em tela cheia, "Começar agora" ou "Já tenho uma conta".
2. **Criar conta** (`cadastro.html`) — nome, e-mail e senha com validação em tempo real,
   medidor de força da senha e, na sequência, os 6 campos do código de verificação.
3. **Entrar** (`login.html`) — e-mail e senha.
4. **Seus interesses** (`interesses.html`) — interesses, orçamento e cidade.
5. **Início** (`app.html`) — saudação, busca, filtros por categoria, carrossel "Para você",
   lista "Explore mais", abas Explorar / Salvos / Perfil e detalhes de cada lugar.
6. **Vai** (`chat.html`) — assistente de IA com sugestões rápidas e histórico.

---

## Testes

```bash
python -m backend.tests.test_regras
```

Cobre as validações de e-mail, senha, nome, código e orçamento, o cálculo de distância, o motor
de match e o assistente local.
