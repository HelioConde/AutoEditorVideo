# Teste GPT4Free -> openai_image -> Arquivo Otaku (v0.3.1)

**Meta:** validar UMA imagem antes de gerar videos inteiros. Nao existe garantia de provedor gratuito online nem qualidade comercial.

## 0 - Abrir PowerShell em C:\Users\helio\Documents\arquivo-otaku-kit

Se `uv --version` nao funcionar, instale com `winget install --id=astral-sh.uv -e`, depois reabra PowerShell.

## 1 - Instalar GPT4Free (primeira vez)

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\instalar-gpt4free.ps1
```

O teste usa `.g4f-venv`, sem alterar `.venv` do MoneyPrinterTurbo. Pina GPT4Free 8.8.6 para manter reproduzibilidade.

## 2 - Abrir API (PowerShell 1, mantenha aberto)

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\iniciar-gpt4free.ps1
```

Servidor local: `http://127.0.0.1:1337/docs`. Escuta somente no loopback do PC.

## 3 - Testar somente UMA imagem (PowerShell 2)

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\testar-gpt4free.ps1
```

A imagem so sera criada se um provedor responder. Verifique `assets\gerados\teste-gpt4free.png`. Erros HTTP 500 ou timeout geralmente indicam provedor indisponivel / autenticação / dependencias.

## 4 - Integrar ao MoneyPrinterTurbo (somente DEPOIS que a imagem funcionar)

O kit principal deve estar instalado (`scripts\instalar-windows.ps1`):

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\configurar-gpt4free.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\rodar-piloto.ps1 -Modo validar -Imagens gpt4free
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\rodar-piloto.ps1 -Modo renderizar -Imagens gpt4free
```

Em `.mpt-runtime/config.toml`, o script coloca:

```toml
[app]
video_source = "openai_image"
openai_image_base_url = "http://127.0.0.1:1337/v1"
openai_image_model = "flux"
openai_image_api_keys = []
openai_image_size = "512x768"
match_materials_to_script = true
video_clip_duration = 6
```

O modo `gpt4free` utiliza `cenas[].prompt_imagem` do episodio e nao cartelas. Ele pode gerar seis requisicoes (uma por cena), mas para depois de completar o audio. Nao use a renderizacao completa sem testar uma imagem.

## Ressalvas de uso

- `GPT4Free` e gratis para instalar. Provedores podem pedir login, ter creditos, apresentar indisponibilidade, ou restringir uso comercial. Consulte termos do provedor selecionado.
- Nenhuma API paga e configurada por este kit. Nao cole suas credenciais nem publique `config.toml`.
- A qualidade e a disponibilidade ainda precisam ser verificadas na maquina Windows; a integracao foi verificada por testes simulados.
- Nao confundir ilustracao original inspirada no clima com imagens oficiais de animes; revise direitos para monetizacao.
- Referencia: https://github.com/xtekky/gpt4free e https://github.com/harry0703/MoneyPrinterTurbo

## Correcao v0.3.1 — SyntaxError no PowerShell 5.1

O instalador anterior executava `python -c` com `print("texto")`. No Windows PowerShell 5.1, as aspas internas podiam desaparecer na passagem dos argumentos para o Python.

O novo script faz apenas `import g4f, fastapi, PIL` e imprime a mensagem de sucesso no proprio PowerShell. Corrigimos pelo mesmo motivo a verificacao do `instalar-windows.ps1`.

**Se a instalacao de pacotes terminou e somente o `SyntaxError` apareceu, nao precisa reinstalar**. Execute:

```powershell
.\.g4f-venv\Scripts\python.exe -c 'import g4f, fastapi, PIL'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\iniciar-gpt4free.ps1
```

Depois, em **outra** janela do PowerShell:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\testar-gpt4free.ps1
```
