# Credenciais GitHub Actions — Proxy e YouTube

O repositório é público: **não fazer commit de chaves, fotos privadas, tokens, JSON OAuth, logs de autenticação nem vídeos privados**.

## A configuração é feita por você no GitHub

Abra `https://github.com/HelioConde/AutoEditorVideo/settings/secrets/actions` → **New repository secret**.
Cadastre, individualmente:

| Nome | Valor a copiar de seu computador/Google Cloud |
| --- | --- |
| `PROXY_API_KEY` | Valor de `PROXY_API_KEY` do `chatgpt-codex-proxy/.env` (somente o valor, sem o prefixo) |
| `YOUTUBE_OAUTH_CLIENT_JSON` | JSON completo do cliente OAuth de aplicativo instalado do Google Cloud |
| `YOUTUBE_BR_TOKEN_JSON` | Conteúdo completo de `.secrets/youtube-token.json` (Otaku Multicena BR) |
| `YOUTUBE_EN_TOKEN_JSON` | Conteúdo completo de `.secrets/youtube-en-token.json` (Otaku Reframe EN) |
| `YOUTUBE_KIDS_TOKEN_JSON` | Conteúdo de token OAuth separado do canal Kids **quando ele estiver autorizado**; opcional por enquanto |

Não cole valores em PRs, issues, comentários, chat, repositório ou logs.

## Testar a configuração sem gastar cota

Em **Actions** → **Credentials - verify Actions Secrets (no API calls)** → **Run workflow**, execute o teste manual. O resultado mostra apenas `OK`, `PENDENTE` ou `INVALIDO`, nunca os conteúdos. O token Kids é opcional. O workflow não chama APIs externas, não usa a chave para gerar imagens e não publica vídeos.

**Limites dessa verificação:** aprova apenas presença e formato de JSON. Não confirma autenticidade, conta elegível no proxy, permissões do Google nem a identidade do canal.

A validação utiliza somente a biblioteca padrão do Python. Há testes sem rede em `tests/test_github_actions_secrets.py`.

## Uso no software

- O gerador de imagens via `scripts/gerar_video_codex.py:proxy_key()` lê `PROXY_API_KEY` do ambiente quando definido, com fallback para o `.env` local. A chave **não cria nem inicia o serviço do proxy**: o código ainda espera `127.0.0.1:8080`, que precisa ser executado no mesmo runner ou ser explicitamente adaptado para um endpoint seguro.
- Para uma futura execução autorizada de upload, o script `scripts/github_actions_secrets.py --stage-channel br` (ou `en`/`kids`) pode criar os arquivos OAuth exigidos pelos scripts existentes em `.secrets/`. Esse comando **não envia vídeos** e se recusa a substituir arquivos existentes. Não execute em jobs de teste ou pull requests.
- O token EN só é utilizado para EN, o token BR só para BR. A verificação do Channel ID no uploader EN permanece necessária.
- Os tokens OAuth podem expirar ou ter seus refresh tokens revogados. Atualize o Secret de acordo com o estado da conta; nunca registre token em artefatos.
- Recomendado para publicar: criar **GitHub Environment** protegido com aprovação manual, limitar branches e configurar secrets específicos do ambiente, evitando exposição desnecessária em jobs gerais.
- Evite `set -x`, `printenv`, dumps de contexto e o upload do diretório `.secrets`.

## Não há publicação automática

Este ajuste apenas prepara o armazenamento seguro e uma conferência de configuração. Os workflows Kids de testes continuam isolados sem acesso às credenciais. Integração com envio efetivo, fotos privadas ou backend persistente requer trabalho posterior e autorização separada.


## Gerar as credenciais com segurança no Windows — sem publicar vídeos

### A. Chave do proxy de imagens

O script `testar-codex-proxy.ps1 -Acao instalar` já cria uma chave forte em
`chatgpt-codex-proxy/.env` na primeira instalação. Se o arquivo já existe,
**não gere outra chave aleatória**: isso desvincularia o cliente do servidor.

Para enviar a chave existente ao Actions Secrets sem mostrá-la no terminal:

```powershell
cd "$HOME\Documents\arquivo-otaku-github"
gh auth login
.\configurar-secrets-github.ps1 -Acao Proxy
```

Se `gh` não estiver instalado: `winget install --id GitHub.cli -e`;
abra outro terminal e depois faça `gh auth login`.
O helper procura também a instalação antiga em `arquivo-otaku-kit`.
Uma chave local **não** transfere automaticamente sessões/tokens de login
do serviço de terceiros para a nuvem.

### B. Cliente OAuth do YouTube, criado pelo Google

No `https://console.cloud.google.com/`, selecione/crie projeto →
**APIs e serviços → Biblioteca → YouTube Data API v3 → Ativar**.
Configure **Google Auth Platform → Branding/Audience/Data Access**, adicione
sua conta como usuário de teste quando aplicável, e em
**Google Auth Platform → Clients → Create client**, selecione
**Desktop app**. Baixe o JSON, renomeie para
`.secrets/youtube-oauth-client.json`. Use a opção de app para desktop,
não uma API key comum.

**Aviso:** se o app OAuth externo permanecer no modo **Testing**, os
refresh tokens de escopos YouTube geralmente expiram em 7 dias.
Para uma integração duradoura, analise o processo e requisitos de
publicação/produção/verificação do Google.

### C. Gerar um token OAuth distinto para cada canal sem upload

No YouTube Studio de cada canal, obtenha o **Channel ID** em
**Configurações → Canal → Configurações avançadas** (começa com `UC`).
Instale as dependências Python do projeto em ambiente virtual. Então:

```powershell
# A partir da raiz do projeto, com venv já instalado:
.\.venv\Scripts\python.exe -m pip install -r requirements-publicacao.txt
.\.venv\Scripts\python.exe scripts\autorizar_youtube_canais.py --canal br --channel-id UC_SEU_ID_REAL_BR
.\.venv\Scripts\python.exe scripts\autorizar_youtube_canais.py --canal en --channel-id UC_SEU_ID_REAL_EN
```

Substitua cada `UC_SEU_ID_REAL_...` por um Channel ID verdadeiro.
O navegador abrirá o login OAuth oficial do Google. Escolha a conta/
canal correspondente. O script usa apenas `channels.list(mine=true)` para
confirmar a identidade, então salva o token privado **sem enviar vídeos**.

Se você já tem tokens locais, o script os preserva. Não é necessário
refazer a autorização só para armazená-los no GitHub. Para reautorizar
um token inválido use `--renovar`; o script salva um backup e não
sobrescreve um backup anterior. Cada canal guarda seu próprio token.

### D. Enviar os JSONs aos Secrets automaticamente, sem exibi-los

```powershell
.\configurar-secrets-github.ps1 -Acao YouTube -Canal br
.\configurar-secrets-github.ps1 -Acao YouTube -Canal en
# Quando o canal Kids estiver pronto:
.\configurar-secrets-github.ps1 -Acao YouTube -Canal kids
```

Esse script usa `gh secret set` por **entrada padrão**. Não inclua o valor
das chaves nos argumentos de linha de comando. Ele não publica nada.
Para verificar nomes cadastrados, use `gh secret list -R HelioConde/AutoEditorVideo`
(a listagem não mostra os valores). Depois faça o merge do PR e rode o
workflow de validação manual.

O script em si e os testes não contêm credenciais privadas.
