# Arquivo Otaku — Atualização de direção visual e publicação v0.6

Esta é uma atualização **incremental** do projeto já instalado em Windows. Não contém suas credenciais, seu vídeo publicado nem as imagens privadas. Mescle os arquivos deste ZIP sobre `C:\Users\helio\Documents\arquivo-otaku-kit`.

## O que muda

1. `conteudos/001-death-note-direcao.json` — novo roteiro/gancho e storyboard de 7 cenas diferentes (Light e L, retrato, objeto, xadrez, ambiente, desfecho). O episódio antigo não é sobrescrito.
2. `scripts/diretor_visual.py` — prompts consistentes com personagens 2D, luminância e correção de sombras *antes* da montagem, hash perceptual que avisa sobre cenas muito similares, QA JSON sem IA extra.
3. `scripts/gerar_video_codex.py` — gerador em **duas fases**: solicita cenas ao Codex Proxy apenas quando não estão em cache; corrige o arquivo; monta pelo MoneyPrinterTurbo com `video_source=local` e imagens na pasta segura `MPT_HOME/storage/local_videos`. Uma chamada de imagem por cena não armazenada em cache; até 7 cenas no piloto.
4. `gerar-video-codex.ps1` — comando Windows para criar **novo** `arquivo-otaku-piloto-codex-v06.mp4`. Não substitui o vídeo anterior e não faz upload.
5. `scripts/publicar_arquivo_otaku.py` — capas redesenhadas e metadados genéricos para outras séries, histórico de uploads por SHA-256 e controle de duplicatas.
6. `publicar-youtube.ps1` — aceita `-Video` e `-Episodio`, com `-Privacidade public` como padrão **somente quando a etapa solicitada for enviar/tudo**, conforme sua preferência anterior. `-Etapa preparar` não publica nada.

## Primeiro: verificar o plano (sem usar cota de imagem)

```powershell
cd C:\Users\helio\Documents\arquivo-otaku-kit
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\gerar-video-codex.ps1 -SomenteConfigurar
```

## Depois: gerar o novo MP4 para inspecionar

Certifique-se de que o Docker Desktop, o Codex Proxy e sua conta estejam disponíveis.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\gerar-video-codex.ps1 -Modelo gpt-image-1.5
```

O gerador consulta `http://127.0.0.1:8080` pelo proxy já autenticado. Saídas:

- `assets\gerados\arquivo-otaku-piloto-codex-v06.mp4` — novo vídeo; **não envia sozinho**.
- `assets\gerados\qa-visual-v06.json` — luminosidade antes e depois, alertas sobre cenas repetidas.
- `assets\gerados\plano-visual-v06.json` — storyboard e narração.
- `.mpt-runtime\storage\local_videos\arquivo-otaku-v06-*` — materiais originais e corrigidos. Não apague para não consumir novamente a cota do modelo.

Quando o vídeo falhar na edição, execute o mesmo comando: cenas existentes com mesmo modelo/prompt são reaproveitadas sem novas chamadas de imagem.

## Apenas revisar as cenas armazenadas — sem uso de IA

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\gerar-video-codex.ps1 -ApenasQA
```

## Preparar novas capas, título e descrição sem publicar

O título fica no arquivo `metadata.json` para revisão antes do envio. A mesma capa deve ter legenda textual legível na tela do celular. Para o vídeo novo:

```powershell
$novo = '.\assets\gerados\arquivo-otaku-piloto-codex-v06.mp4'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\publicar-youtube.ps1 -Etapa preparar -Video $novo -Refazer
```

**Atenção:** `-Refazer` recria `metadata.json` e as capas a partir do material local ou da arte salva. Revise qualquer texto que você tenha editado manualmente antes de usar.

## Publicar o novo vídeo no YouTube

Somente depois de inspecionar o MP4 e conferir `metadata.json`:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\publicar-youtube.ps1 -Etapa enviar -Video '.\assets\gerados\arquivo-otaku-piloto-codex-v06.mp4' -Privacidade public
```

Esta etapa chama a API oficial do YouTube, usando o OAuth **já configurado localmente**. Um arquivo `estado-upload-<hash>.json` evita repetir upload do mesmo MP4 quando a operação já foi concluída.

Alternativamente, para **gerar um vídeo novo e enviar ao YouTube de uma só vez** depois que você tiver validado o fluxo:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\publicar-youtube.ps1 -GerarVideo -Etapa tudo -Privacidade public
```

O usuário ainda precisa executar esse comando explicitamente. Atenção: o YouTube pode impor restrições de visibilidade a projetos de API não verificados; verifique a privacidade final no Studio.

## Segurança, recursos e limitações

- Nenhum script precisa que você compartilhe `.env`, `.secrets` ou tokens OAuth.
- A geração gpt-image usa uma interface de proxy **não oficial**, sujeita à disponibilidade e às cotas da conta. Não é garantidamente gratuita ou ilimitada.
- O sistema confere se há conta elegível antes das imagens novas, mas isso **não garante** acesso ao modelo nem que cotas não serão consumidas.
- A inspeção de semelhança usa diferença de hash e **avisa**; não gera imagens extras automaticamente. Inspecione rostos/mãos manualmente.
- O QA ilumina moderadamente as sombras, mas não consegue corrigir anatomia ou mudar a expressão após gerar.
- Esta versão não altera vídeos existentes e não publica nada ao instalar o ZIP.
- A capa de Shorts pode não aparecer como miniatura personalizada em todas as superfícies do YouTube.

## Diagnóstico

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\publicar-youtube.ps1 -Etapa diagnostico
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\testar-codex-proxy.ps1 -Acao status
```

## Arquivos a preservar

Nunca substitua ou apague os seguintes arquivos/pastas do seu computador:

- `.secrets/`
- `chatgpt-codex-proxy/.env`
- `assets/gerados/` (incluindo `estado-upload.json` e `estado-upload-*.json`)
- `.mpt-runtime/storage/local_videos/` (cache de cenas)
- Seu vídeo anterior `arquivo-otaku-piloto-codex.mp4`.

### Validação

As funções de QA, cache, argumentos de render, capas, publicação e validação do plano passaram em 10 testes automatizados **sem usar a conta Codex Proxy e sem subir um novo vídeo para o YouTube**. A execução real em Windows continua por validar.
