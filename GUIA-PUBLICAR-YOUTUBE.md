# Arquivo Otaku — Publicação YouTube v0.5.1

## Correções desta versão
- `-Etapa tudo` verifica a presença e o formato do OAuth **antes** de solicitar novas imagens ou texto por IA; economiza cotas quando o upload ainda não pode começar.
- `-Etapa diagnostico` verifica MP4, capas, metadados, arquivo OAuth e elegibilidade de contas no Codex Proxy. **Não envia vídeos nem solicita novas imagens**.
- `-Etapa preparar` funciona sem OAuth, mantém metadados existentes (a menos que use `-Refazer`).
- `estado-upload.json` continua impedindo repetir um upload confirmado quando a miniatura falha.
- Privacidade padrão: `private`.

## Instalar
Extraia este ZIP na pasta `C:\Users\helio\Documents\arquivo-otaku-kit`, substituindo os scripts antigos. **Não apague** o MP4 existente, `.secrets/` ou `assets/gerados/`.

## Diagnóstico seguro
Abra o PowerShell dentro de `arquivo-otaku-kit`:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\publicar-youtube.ps1 -Etapa diagnostico
```

Se o proxy exibir `elegiveis agora: 0`, verifique o status da conta via:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\testar-codex-proxy.ps1 -Acao status
```

Não é necessário gerar imagens novas para publicar o primeiro vídeo: as miniaturas e metadados locais já estão disponíveis.

## Criar credenciais OAuth oficiais do YouTube
1. Abra https://console.cloud.google.com/ e crie/selecione um projeto, por exemplo `Arquivo Otaku Upload`.
2. Em **APIs e serviços > Biblioteca**, habilite **YouTube Data API v3**.
3. Em **Google Auth Platform > Branding** (tela de consentimento OAuth), informe nome do app e e-mail.
4. Em **Audience / Público**, selecione `External / Externo` se usar uma conta Google pessoal; se permanecer em `Testing / Testando`, adicione sua própria conta Google em **Test users / Usuários de teste**.
5. Em **Google Auth Platform > Clients / Clientes**, clique **Create client / Criar cliente**, selecione **Desktop app / Aplicativo para computador**. Não é *Aplicativo Web*, *Conta de serviço* nem *Chave de API*.
6. Baixe o JSON e renomeie para **youtube-oauth-client.json**.
7. Salve em `C:\Users\helio\Documents\arquivo-otaku-kit\.secrets\youtube-oauth-client.json`.
8. Verifique localmente que o arquivo existe:

```powershell
New-Item -ItemType Directory -Path '.\.secrets' -Force | Out-Null
Test-Path '.\.secrets\youtube-oauth-client.json'
```

O resultado deve ser `True`. **Não envie** o JSON, tokens, códigos OAuth ou `.env` para o chat nem para o GitHub. O primeiro envio solicitará autorização pelo navegador na conta Google que administra o canal.

## Preparar capas e título sem usar IA
```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\publicar-youtube.ps1 -Etapa preparar
```

Confira `assets\gerados\publicacao-youtube\metadata.json`, `miniatura-youtube.jpg` e `capa-tiktok-shorts.jpg` antes de publicar.

## Enviar o vídeo pronto — privado por padrão
```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\publicar-youtube.ps1 -Etapa enviar
```

Quando estiver tudo configurado, pode usar `-Etapa tudo` (sem `-ArteIA`/`-TextoIA`, pois estas opções consomem cota do proxy). **Somente** use `-Privacidade public` após decidir tornar o vídeo público. Confira a privacidade real no YouTube Studio: os requisitos de verificação do projeto podem limitar o resultado. O YouTube pode rejeitar thumbnails de Shorts por API sem que o upload do vídeo falhe.

## Referências oficiais
- https://developers.google.com/youtube/data/quickstart/python
- https://developers.google.com/youtube/data/guides/auth/installed-apps
- https://developers.google.com/youtube/data/reference/rest/v3/videos/insert
- https://developers.google.com/youtube/data/reference/rest/v3/thumbnails/set
