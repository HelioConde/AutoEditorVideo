# GitHub Environment `image-generation` — Fofinhos sem Docker

Os testes nativos do Go no Actions já passaram. Este procedimento apenas prepara
um Environment e valida sessões **sem gerar imagens e sem publicar vídeos**.

## Limites e segurança

- O repositório é público: nunca commitar `accounts.json`, fotos, `.env`, OAuth ou MP4 privado.
- `PROXY_API_KEY` (Repository Secret já existente) protege a API HTTP.
- `PROXY_ACCOUNTS_JSON` é um **Environment Secret separado** e contém acesso OAuth à conta;
  nunca guardá-lo em Variables. Não se confunde com tokens do YouTube.
- O GitHub conectado ao ChatGPT não oferece a administração de Environments/Secrets;
  a criação do ambiente exige o GitHub CLI com permissão de administração no Windows.
- `MAX_IMAGE_CALLS=0` é configurado por padrão. Nenhum workflow aqui gera imagens.

## Criar Environment protegido, somente branch main

Depois do merge do PR correspondente, execute no PowerShell:

```powershell
cd C:\Users\helio\Documents\arquivo-otaku-github
git pull --ff-only
gh auth status
.\configurar-ambiente-imagens-github.ps1 -Acao Preparar
.\configurar-ambiente-imagens-github.ps1 -Acao Status
```

O script cria `image-generation` com uma única política de deployment para `main`,
e define `IMAGE_MODEL=gpt-image-2`, `MAX_IMAGE_CALLS=0`, `PROXY_PORT=8080`.
Se o Environment já existir com políticas diferentes, falha sem enfraquecer regras.
Revise em https://github.com/HelioConde/AutoEditorVideo/settings/environments

## Verificar primeiro sem credenciais reais

Workflow: `.github/workflows/fofinhos-image-generation-environment.yml`.
Executar com o input `validate_private_session=false` roda só testes sintéticos.
Em PR e push nenhum Secret privado é disponibilizado.

## Importar estado OAuth — somente com autorização consciente

O projeto Go original salva `DATA_DIR/accounts.json`, contendo access/refresh tokens.
O arquivo frequentemente fica no Docker em `/app/data/accounts.json`.
Não envie esse arquivo ao chat, nem a GitHub Issues ou artefatos.

```powershell
# Opção 1 — buscar do contêiner Docker local (pede confirmação AUTORIZO)
.\configurar-ambiente-imagens-github.ps1 -Acao ImportarSessao

# Opção 2 — usar arquivo privado local já existente
.\configurar-ambiente-imagens-github.ps1 -Acao ImportarSessao -Arquivo 'C:\CAMINHO-PRIVADO\accounts.json'
```

O script verifica a estrutura e tamanho (até 45 KiB), exige confirmação,
transmite apenas por stdin com `gh secret set ... -e image-generation` e
remove a cópia temporária. Se o arquivo não couber, aborta sem dividir tokens.

## Consulta protegida, sem geração

```powershell
gh workflow run fofinhos-image-generation-environment.yml -R HelioConde/AutoEditorVideo --ref main -f validate_private_session=true
```

Antes do job com Secrets, outro job consulta a API do GitHub e confirma que
o Environment existe e permite **exatamente a branch `main`**.
Depois compila o binário Go em commit fixado, restaura `accounts.json` temporário
com permissão 0600 e faz somente `GET /health/live` e `GET /admin/accounts`.
Não há chamadas de imagens, uploads, renovação explícita ou coleta de cookies.
Os resultados mostram somente presença de contas e elegibilidade em cache;
isso **não prova** acesso real ao serviço de imagens da conta.

## Persistência de tokens — bloqueio para produção

O proxy pode renovar OAuth e regravar `accounts.json` durante o uso.
Um Environment Secret é uma cópia inicial: **não é atualizado automaticamente**
com o estado novo do runner. Por isso, o teste é read-only e temporário.
Antes de ativar geração real, projetar armazenamento privado persistente,
revisar riscos do proxy comunitário (API não documentada), cota e permissões.

Nenhum token precisa ser compartilhado com o ChatGPT.
