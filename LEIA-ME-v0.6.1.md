# Arquivo Otaku — correção v0.6.1

Quando `Nenhuma conta elegivel no Codex Proxy` aparece, as 7 cenas novas não foram geradas. O problema pode resultar de sessão expirada, conta desabilitada, cooldown ou cota esgotada. **Esta atualização não contorna os limites de uso da conta**.

## 1. Instalar

Extraia o ZIP dentro de `C:\Users\helio\Documents\arquivo-otaku-kit`, mesclando as pastas. Não apague `.secrets`, `.mpt-runtime`, `chatgpt-codex-proxy/.env` nem `assets/gerados`.

## 2. Diagnosticar o Codex Proxy (sem gastar cotas)

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\diagnosticar-proxy.ps1
```

Se a conta estiver ativa mas temporariamente indisponível, aguarde e tente a geração normal quando `Elegivel: True` retornar. Se não houver conta, execute `testar-codex-proxy.ps1 -Acao login`. Não repita o login se o problema for cota esgotada.

## 3. Continuar a edição sem nenhuma nova chamada de IA

Este modo aproveita as imagens da primeira versão. Ele NÃO cria sete imagens novas nem promete correspondência perfeita com o storyboard revisado. As imagens serão corrigidas de iluminação e usadas na montagem com o roteiro novo, narração e legendas.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\gerar-video-codex.ps1 -ReutilizarImagens
```

O script procura `openai-image-*.png` nas seguintes pastas:

- `assets/gerados/imagens-reutilizadas`
- `assets/gerados`
- `.mpt-runtime/storage/tasks` (incluindo subpastas)

Se não encontrar ao menos três imagens, copie as imagens PNG do primeiro vídeo para `assets\gerados\imagens-reutilizadas` ou informe a pasta onde elas estão:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\gerar-video-codex.ps1 -ReutilizarImagens -PastaImagens 'C:\CAMINHO\DAS\IMAGENS'
```

O novo MP4 fica em:

`assets\gerados\arquivo-otaku-piloto-v061-reuso.mp4`

Essa versão utiliza até sete clipes, mas pode **repetir imagens** se houver menos que sete arquivos distintos. Não gasta cota de geração de imagens. O TTS pode requerer acesso à internet.

## 4. Gerar cenas realmente novas quando houver cota

O comando original continua disponível:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\gerar-video-codex.ps1 -Modelo gpt-image-1.5
```

Ele não publica automaticamente. Para enviar, confira o MP4 e use a etapa `enviar` do `publicar-youtube.ps1`, apontando explicitamente para o novo arquivo. A privacidade do envio depende do parâmetro `-Privacidade`.

## Garantias e limites

- O modo de reutilização **não acessa** os endpoints do Codex Proxy e não usa créditos de IA.
- Não modifica nem exclui a versão do YouTube já publicada.
- O pacote não inclui segredos, tokens ou vídeos privados.
- Apenas os testes locais foram executados; não foi possível executar o MoneyPrinterTurbo no Windows do usuário.
- Se as imagens antigas não estiverem no disco, será necessário fornecer sua pasta ou esperar cota para gerar as novas.
