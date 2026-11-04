# Publicar o Viajaí gratuitamente

O Viajaí é uma aplicação Flask (Python) com banco SQLite e fotos enviadas em disco. Hospedagem
compartilhada comum (ex.: a da Hostinger) não roda Python; é preciso um serviço que rode Flask.
Os limites abaixo mudam com o tempo — confirme na página do serviço antes de começar.

## Qual escolher

| Serviço (plano gratuito) | Banco e fotos persistem? | Observações |
|---|---|---|
| **PythonAnywhere** (recomendado) | **Sim** (disco permanente) | Sem cartão. Endereço `seu-usuario.pythonanywhere.com`. Só acessa a internet para sites de uma lista permitida, então parte das integrações pode ficar indisponível. Pede para você clicar em "renovar" periodicamente. |
| **Render** | **Não** — disco apagado a cada deploy/reinício | Serve só para demonstração. Hiberna após alguns minutos sem uso e demora a acordar. |

O app funciona mesmo quando as integrações externas estão bloqueadas (mapas de fundo, fotos da
Wikimedia, estabelecimentos do OpenStreetMap, clima): ele mostra avisos em vez de quebrar.

## Variáveis de ambiente (obrigatórias em produção)

| Variável | Valor |
|---|---|
| `FLASK_DEBUG` | `0` |
| `SECRET_KEY` | texto longo e aleatório (`python -c "import secrets;print(secrets.token_hex(32))"`). O app **se recusa a subir** sem ela. |
| `HTTP_USER_AGENT` | `Viajai/2.0 (contato: seu-email@exemplo.com)` |
| `GEMINI_API_KEY` | opcional (gratuita em aistudio.google.com/apikey) |

### Código de verificação do cadastro

Com `FLASK_DEBUG=0` o código **não aparece na tela**. Escolha um jeito de entregá-lo:

1. **E-mail de verdade (recomendado):** `EMAIL_MODO=smtp`, `SMTP_HOST=smtp.gmail.com`, `SMTP_PORTA=587`,
   `SMTP_USUARIO=seu@gmail.com`, `SMTP_SENHA=` *senha de app* do Google (Conta Google → Segurança →
   Senhas de app), `EMAIL_REMETENTE=seu@gmail.com`.
2. **Só para demonstração entre conhecidos:** deixe `EMAIL_MODO=console`; o código aparece no log do
   servidor (aba *Log files* no PythonAnywhere) e você repassa à pessoa.

## PythonAnywhere — passo a passo

1. Crie a conta gratuita em pythonanywhere.com.
2. Abra um **Bash console** e rode:
   ```bash
   git clone https://github.com/joaof1w/viajai.git
   cd viajai && git checkout claude/viajal-12-features-expansion-oj11sr
   python3 -m venv ~/venv && source ~/venv/bin/activate
   pip install -r requirements.txt
   ```
3. Aba **Web → Add a new web app → Manual configuration** (Python 3.10 ou superior).
4. Em **Virtualenv**, informe `/home/SEU_USUARIO/venv`.
5. Em **Code → WSGI configuration file**, apague o conteúdo e use:
   ```python
   import os, sys
   sys.path.insert(0, "/home/SEU_USUARIO/viajai")
   os.environ["FLASK_DEBUG"] = "0"
   os.environ["SECRET_KEY"] = "COLE_SUA_CHAVE_AQUI"
   os.environ["HTTP_USER_AGENT"] = "Viajai/2.0 (contato: seu-email@exemplo.com)"
   # os.environ["GEMINI_API_KEY"] = "..."
   # E-mail: EMAIL_MODO, SMTP_HOST, SMTP_PORTA, SMTP_USUARIO, SMTP_SENHA, EMAIL_REMETENTE
   from wsgi import app as application
   ```
6. Clique em **Reload**. Abra `https://SEU_USUARIO.pythonanywhere.com`.
7. O banco (`backend/viajai.db`) e as fotos (`backend/uploads`) ficam no disco e permanecem.

Fotos reais dos lugares (precisam de acesso à Wikimedia, que pode estar fora da lista permitida):
`python -m tools.fotos sincronizar` no console. Se estiver bloqueado, os lugares exibem a
ilustração com o aviso de que não há foto verificada.

## Render — resumo (demonstração)

New → Blueprint → aponte para o repositório e a branch. O `render.yaml` já configura tudo e gera a
`SECRET_KEY`. Lembre que o banco volta ao zero a cada deploy.
