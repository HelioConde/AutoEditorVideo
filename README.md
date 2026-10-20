# AutoEditor Studio 2.1 — Desktop e Web

Estúdio para **importar, recortar, pré-visualizar e exportar vídeos** sem depender de uma API paga. Desenvolvimento inicial a partir de [AutoEditorVideo (2022)](https://github.com/HelioConde/AutoEditorVideo). Código original preservado em `legacy/` e no histórico do Git.

## Funcionalidades implementadas

- Dashboard com projetos persistidos em disco, status real do FFmpeg e contagens reais.
- Projetos com nomes validados, importação de MP4/MOV/WebM/MKV até 512 MB e preview com controles nativos.
- Recorte por tempo inicial/final e exportação local para 9:16 (720x1280) ou 16:9 (1280x720), H.264 + AAC, MP4.
- Consulta do status da exportação e link de download.
- UI responsiva em português com foco visível, formulário com labels, navegação por teclado e estados de erro.
- Testes de API (Node test), E2E desktop e mobile (Playwright), screenshots e CI.

**Não implementado:** transcrição Whisper, narração Kokoro, corte automático de silêncios, geração de vídeo por IA ou postagem automática. Essas opções são identificadas como futuras na interface.

## Requisitos

- Node.js **22+**, npm.
- [FFmpeg e FFprobe](https://ffmpeg.org/download.html) acessíveis pelo PATH do sistema. Verifique com `ffmpeg -version` e `ffprobe -version`.
- Windows, Linux ou macOS. A API escuta **somente em 127.0.0.1**.

## Executar (Windows PowerShell)

```powershell
git clone https://github.com/HelioConde/AutoEditorVideo.git
cd AutoEditorVideo
npm install
npm run dev
```

Acesse **http://127.0.0.1:5173**. `npm run dev` inicia o serviço Node local na porta 3011 e o Vite na porta 5173. Os projetos e vídeos ficam no diretório `data/`, ignorado pelo Git. O navegador não envia mídia para serviços externos; fontes do Google Fonts podem ser requisitadas para o visual (há fontes substitutas locais se estiver offline).

**Produção local**: `npm run build` e `npm start` disponibilizam a interface e API na porta 3011.

## Qualidade

```bash
npm run test           # testes de API
npm run build          # build React/Vite
npx playwright install chromium
npm run test:e2e       # interface desktop/mobile, captura de tela e exportação real
```

As capturas são gravadas em `test-results/`. No GitHub Actions ficam disponíveis como artefatos de CI. Antes de rodar E2E, encerre instâncias do `npm run dev` que usem as mesmas portas.

## Segurança e limites

- Apenas arquivos locais de vídeo são aceitos; nenhuma URL arbitrária é baixada. FFprobe valida se a mídia contém vídeo.
- A API grava arquivos em diretórios com UUID; nomes enviados não são usados como caminho.
- Bloqueia operações de escrita com Origin divergente do ambiente local esperado e não habilita CORS.
- **Não publique a API diretamente na internet**: ainda não há autenticação, quotas por usuário ou isolamento para uso multiusuário.
- Arquivos grandes exigem espaço livre e podem consumir CPU significativamente. Exportações devem ser testadas com vídeos próprios.
- O sistema é um **MVP** e ainda não suporta fila persistente após reinício ou cancelamento do FFmpeg.

## Próximas etapas

1. Miniaturas e timeline com quadro real, arrastar marcadores e salvar presets.
2. Whisper local para transcrição e legendas SRT editáveis.
3. Remoção de silêncios com detecção de voz e revisão.
4. Narração Kokoro local com avaliação de modelos e licenças.
5. Templates Remotion e automações para Shorts.


## Edição web: GitHub Pages

**Endereço previsto:** https://helioconde.github.io/AutoEditorVideo/

O modo web é **100% estático e separado da API Node**, permitindo cortes e exportações MP4 no próprio navegador usando FFmpeg WebAssembly. Aceita MP4/WebM até 30 MB e 2 minutos; exporta trechos até 20 segundos. Precisa baixar o motor na primeira exportação (~31 MB); nenhuma mídia é enviada para servidores. Pode ser lento em celulares.

Para rodar localmente: `npm run dev:web` (http://127.0.0.1:5174). Para gerar: `npm run build:web`. Para testes: `npm run test:e2e:web`.

**Ativação inicial do site:** em [Settings → Pages](https://github.com/HelioConde/AutoEditorVideo/settings/pages), escolha **GitHub Actions** como fonte. O workflow `.github/workflows/pages.yml` cuida dos próximos builds e deployments. Verifique status antes de divulgar o site. Veja [docs/WEB_EDITION.md](docs/WEB_EDITION.md).

## Executar no Windows

Para edição desktop com servidor local, instale Node.js 22+, FFmpeg e FFprobe no PATH, execute `npm install` e `npm run dev`. Acesse http://127.0.0.1:5173.

## Timeline visual e cortes múltiplos

As duas versões exibem **miniaturas reais do vídeo** (geradas localmente pelo navegador), sliders acessíveis para os limites de corte, uma ação de prévia e uma sequência ordenada de até cinco cortes. Use **Adicionar à sequência** para montar uma lista; altere a ordem com as setas ou remova um trecho. Quando a lista está vazia, a exportação continua usando o recorte único; quando há itens, **somente os cortes da lista são unidos**.

O desktop usa FFmpeg nativo e concat demuxer de segmentos reencodados com parâmetros idênticos; duração final máxima de 10 minutos. Na web, o FFmpeg.wasm processa e concatena até cinco trechos somando **20 segundos**. Ambos exigem recursos adequados ao tamanho do vídeo. No desktop, a sequência e o roteiro são salvos no projeto; na web, também são preservados automaticamente em rascunho local no navegador e podem ser exportados em JSON.

## Projetos compartilháveis e vídeo narrado (2.3 beta)

As versões web e desktop compartilham **`autoeditor.project` v1**: exportação/importação `.autoeditor.json` com nome, proporção, marcas de tempo, sequência de cortes, roteiro e cenas. O **vídeo original não é transferido**: precisa ser selecionado novamente no outro dispositivo (o app verifica nome e duração antes de reaproveitar os cortes). A edição desktop é gravada automaticamente nos metadados locais, e a web trabalha em memória, com arquivo JSON para transporte.

O **modo roteiro** transforma parágrafos em até seis cenas editáveis, com título, texto e duração de 2–15 segundos. **Não é geração de imagens ou vídeos por IA**: cria cartões de texto com paleta coerente. A prévia de voz usa a síntese do navegador, em português quando a voz está instalada.

**No desktop**, com FFmpeg instalado e uma voz em português no sistema, `Gerar vídeo narrado` cria slides com narração e exporta MP4:
- **Windows:** usa `System.Speech` via PowerShell e requer uma voz pt-BR/pt-PT instalada em Configurações de Fala. Não instala vozes automaticamente.
- **Linux:** instale `espeak-ng` para disponibilizar narração `pt-br`. O Linux usa a voz sintética do sistema (qualidade inferior a modelos neurais como Kokoro).
- O áudio da cena é limitado à duração configurada; ajuste a duração para evitar cortar a fala. A exportação preserva o roteiro em seu próprio projeto.
- **Site (GitHub Pages):** por enquanto apenas organiza o roteiro e permite ouvir uma prévia da narração. O site **ainda não incorpora essa voz ao MP4 exportado**. Sem backend, `speechSynthesis` não permite capturar diretamente o áudio gerado.

Este passo prepara a infraestrutura compartilhada para incorporar Kokoro/faster-whisper posteriormente, sem apresentar a prévia como exportação de narração.

## Narrador neural opcional: Piper pt-BR (2.4 beta)

O desktop oferece dois motores: **Voz do sistema** (eSpeak NG no Linux; System.Speech no Windows) e **Piper neural local**. O Piper não é instalado ou baixado automaticamente pelo projeto. Para habilitá-lo, instale o executável Piper e obtenha um modelo `.onnx` e seu `.onnx.json` de uma voz brasileira. Exemplo: voz `pt_BR-faber-medium` no catálogo Rhasspy Piper Voices (aprox. 63 MB). Verifique a licença da voz antes de uso comercial.

No PowerShell, antes de `npm run dev`:
```powershell
$env:PIPER_BIN = "C:\\piper\\piper.exe"
$env:PIPER_MODEL = "C:\\piper\\models\\pt_BR-faber-medium.onnx"
npm run dev
```

O arquivo de configuração **`pt_BR-faber-medium.onnx.json` deve ficar ao lado do modelo ONNX**. O app identifica a disponibilidade em `GET /api/health` e não troca silenciosamente a opção Piper por outra voz. Se o modelo não estiver presente, use a voz do sistema. O Piper funciona com CPU, mas a velocidade depende da máquina. No Linux, exporte as mesmas variáveis `PIPER_BIN` e `PIPER_MODEL`.

## Temas, imagens próprias e transições
Cada cena permite escolher um dos seis temas (floresta, oceano, crepúsculo, âmbar, menta, ardósia), uma transição **fade suave** ou **corte direto**, e carregar uma imagem de fundo JPG/PNG/WebP de até **2 MB**. O editor compõe título e narração sobre o fundo localmente; no desktop, isso vira uma cena no MP4. As imagens são tratadas na memória e **não são armazenadas nem transferidas no projeto JSON**; escolha-as novamente após importar ou recarregar.

A renderização agora aumenta automaticamente a duração da cena quando a fala é mais longa que o número definido, para não cortar frases sem aviso. Há um limite de 65 s de fala por cena; se excedido, divida o texto. Transições fade escurecem a entrada e a saída em aproximadamente 350 ms, sem sobreposição de cenas. A prévia de áudio do navegador pode ter voz diferente do Piper utilizado na exportação.

## Legendas e Whisper.cpp local (2.5 beta)

As duas versões agora têm um editor de legendas: importação **SRT ou WebVTT**, edição de texto e horários, pré-visualização conforme o vídeo avança e download separado em `.srt`. Até 120 legendas e uma hora de timestamps; os textos são salvos no `.autoeditor.json` compartilhado. No **desktop**, marque **Gravar legendas no MP4 dos cortes** para que FFmpeg use libass e incorpore texto ao arquivo final. Para vários cortes, os tempos das legendas são remapeados à ordem da sequência. Se FFmpeg não possuir o filtro `subtitles`/libass, desmarque a opção e use o SRT separado. **Na web**, legendas são somente prévia e download separado, não incorporadas ao MP4 do navegador.

A opção **Transcrever áudio** no desktop utiliza um executável Whisper.cpp local (`whisper-cli`), sem enviar dados a serviços de terceiros. Para habilitar, instale whisper.cpp e um modelo multilíngue GGML em seu PC; no Windows configure, por exemplo:
```powershell
$env:WHISPER_BIN = "C:\\whisper.cpp\\build\\bin\\Release\\whisper-cli.exe"
$env:WHISPER_MODEL = "C:\\whisper.cpp\\models\\ggml-base.bin"
npm run dev
```
O editor reconhece o recurso quando modelo e CLI estão disponíveis. Áudio de arquivos de até 10 minutos é convertido em WAV 16 kHz mono pelo FFmpeg e transcrito localmente em português. Revise o texto e os horários, pois modelos de reconhecimento de fala podem errar. Os testes de CI usam um **simulador da interface CLI**, não um modelo Whisper real. Modelos não são distribuídos nem baixados automaticamente pelo aplicativo.

## Timeline de precisão e rascunho automático (2.7 beta)

Na timeline compartilhada com o site e o desktop é possível ajustar o corte em **centésimos de segundo (0,01s)** ou décimos (0,1s), escolher zoom **1×, 2×, 4×, 8×** para as réguas de corte e abrir um trecho da sequência com **Editar**, ajustá-lo e clicar em **Salvar ajuste**. O zoom amplia a **faixa dos sliders**, não o quadro das miniaturas (que permanece exibindo a fonte completa). Os ajustes respeitam o intervalo mínimo de 0,25s e os limites de duração por edição.

A versão web preserva automaticamente o projeto no **localStorage deste navegador** a cada alteração válida (com debounce). Após atualizar ou fechar a página, o editor recupera cortes, roteiro, cenas, legendas, proporção e nome. Para recuperar trechos de mídia, **selecione o vídeo original novamente**; é verificado nome e duração aproximada, não o conteúdo exato. O rascunho **não inclui vídeo, imagens das cenas, MP4 exportado ou dados remotos**. Também há botão **Limpar rascunho**. Navegação privada, limpeza dos dados do navegador e políticas de armazenamento podem eliminar o rascunho; por segurança, exporte seu projeto `.autoeditor.json` regularmente.

## Site 2.8: editor por etapas

A página web abre com apenas **Importar vídeo**. Ao carregar mídia válida, o usuário avança para **Editar cortes** (timeline, seleção e sequência); a configuração de formato e o botão **Exportar MP4** aparecem na terceira etapa, selecionada ao clicar em **Continuar para exportação**. A navegação entre as etapas mantém os valores preenchidos, e o editor impede avançar para corte/exportação sem vídeo.

Legendas, roteiro e projeto JSON são **ferramentas opcionais**: cada uma possui um botão de expansão e somente a ferramenta selecionada é montada. É possível **Criar pelo roteiro** ou **Abrir projeto salvo** sem importar mídia primeiro. O fluxo básico não exige configurar esses módulos. O painel de informações sobre rascunhos fica em uma seção recolhida, acessível pelo resumo **Rascunho no navegador**.

Essa organização reduz a carga visual e evita renderizar timelines e formulários pesados antes de serem necessários. Ela não aumenta os limites técnicos da versão web (30 MB/2 min de entrada e até 20s somados de exportação), nem adiciona contas ou servidores.

## Novo foco: Shorts automáticos (MVP)

O desktop agora pode gerar Shorts verticais independentes, a partir dos destaques sugeridos na transcrição. É necessário transcrever localmente com Whisper.cpp ou importar SRT. Os destaques iniciais usam pontuação por padrões do texto (não inteligência multimodal ou garantia de viralização), são revisáveis e exportados individualmente com legenda incorporada. Saiba mais em [docs/AUTO_SHORTS_MVP.md](docs/AUTO_SHORTS_MVP.md).

## Ranking multimodal local (fase experimental)

O modo desktop oferece uma análise opcional por FFmpeg que combina o texto das legendas com **picos relativos de intensidade no áudio** e **mudanças de cena** amostradas em baixa resolução. O seletor de tipo de vídeo permite escolher podcast, gameplay ou tutorial. As evidências aparecem em cada sugestão; nenhum serviço externo recebe o vídeo. A análise atual aceita até 10 minutos de origem, não identifica emoções, vitórias ou eventos esportivos e ainda requer uma transcrição/SRT para propor cortes. Leia [docs/MULTIMODAL_RANKING.md](docs/MULTIMODAL_RANKING.md) para limitações e próximos passos.

## Revisão de Shorts antes de exportar

Após a análise, cada sugestão tem uma caixa **Incluir Short na exportação**. É possível desmarcar resultados que não fazem sentido e gerar apenas os escolhidos; com nenhum selecionado, a exportação fica desativada. O servidor recalcula as sugestões e valida os intervalos enviados, evitando aceitar um trecho alterado ou desatualizado como se tivesse sido aprovado automaticamente.

Os testes incluem uma gravação sintética com corte visual real entre cenas preta e branca, além de áudio. O Playwright exige que o FFmpeg detecte **amostras de áudio e ao menos uma mudança visual** antes de concluir o fluxo de exportação.
