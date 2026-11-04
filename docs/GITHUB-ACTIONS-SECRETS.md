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
