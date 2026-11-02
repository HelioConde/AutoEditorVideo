# Arquivo Otaku — experimento com ChatGPT Codex Proxy

Fonte: https://github.com/10/chatgpt-codex-proxy

Aviso: projeto independente, não afiliado à OpenAI. Usa interfaces privadas; a autenticação grava tokens no volume do Docker. Uma conta ChatGPT não garante acesso à geração de imagens; o uso pode consumir cotas e não equivale a uma API gratuita e ilimitada. Revise o repositório antes de conectar uma conta.

Executar no Windows PowerShell, dentro da pasta `arquivo-otaku-kit`:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\testar-codex-proxy.ps1 -Acao instalar
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\testar-codex-proxy.ps1 -Acao login
# Abrir o URL fornecido pelo programa, conferir o domínio e autorizar manualmente
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\testar-codex-proxy.ps1 -Acao status
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\testar-codex-proxy.ps1 -Acao imagem
```

Para testar modelo alternativo (somente após checar que a conta oferece acesso):

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\testar-codex-proxy.ps1 -Acao imagem -Modelo gpt-image-1.5
```

O arquivo será salvo em `assets\gerados\teste-codex-proxy.png` se a resposta contiver uma imagem PNG.

Se o proxy funcionar, `openai_image_base_url = "http://127.0.0.1:8080/v1"` e `openai_image_model = "gpt-image-2"` no MoneyPrinterTurbo. Em `openai_image_api_keys` usar a chave local `PROXY_API_KEY` presente em `chatgpt-codex-proxy\.env`, mantida fora do Git e jamais compartilhada. O Arquivo Otaku pode exigir retirar o parâmetro `--video-source local` de `piloto.py` quando for integrar.

### Docker Desktop (Windows)

O comando `docker.exe` sozinho nao indica que o motor Docker esteja funcionando. Antes de instalar, verifique:

```powershell
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
docker version
docker info --format '{{.ServerVersion}}'
wsl --list --verbose
```

Se aparecer `open //./pipe/dockerDesktopLinuxEngine`, o motor Linux esta parado/indisponivel. Abra o Docker Desktop e use **Linux containers**, com WSL 2 ativo. O script v1.1 agora tenta abrir o Docker Desktop e espera o motor responder; nao termina com `NativeCommandError` no primeiro erro nativo.

Se precisar executar `wsl --shutdown`, salve o trabalho aberto nas distribuicoes Linux primeiro; esse comando encerra os processos WSL ativos.

### Diagnóstico

```powershell
cd .\chatgpt-codex-proxy
docker compose ps
docker compose logs --tail 60
```

Para parar:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\testar-codex-proxy.ps1 -Acao parar
```

O `down` **não** elimina o volume com os tokens. Se deixar de confiar no projeto, revogue o acesso à conta conforme as opções disponíveis e apague o volume após decidir perder esses dados.
