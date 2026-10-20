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

O desktop usa FFmpeg nativo e concat demuxer de segmentos reencodados com parâmetros idênticos; duração final máxima de 10 minutos. Na web, o FFmpeg.wasm processa e concatena até cinco trechos somando **20 segundos**. Ambos exigem recursos adequados ao tamanho do vídeo. No desktop, a sequência e o roteiro agora são salvos no projeto; na web, podem ser exportados em JSON.

## Projetos compartilháveis e vídeo narrado (2.3 beta)

As versões web e desktop compartilham **`autoeditor.project` v1**: exportação/importação `.autoeditor.json` com nome, proporção, marcas de tempo, sequência de cortes, roteiro e cenas. O **vídeo original não é transferido**: precisa ser selecionado novamente no outro dispositivo (o app verifica nome e duração antes de reaproveitar os cortes). A edição desktop é gravada automaticamente nos metadados locais, e a web trabalha em memória, com arquivo JSON para transporte.

O **modo roteiro** transforma parágrafos em até seis cenas editáveis, com título, texto e duração de 2–15 segundos. **Não é geração de imagens ou vídeos por IA**: cria cartões de texto com paleta coerente. A prévia de voz usa a síntese do navegador, em português quando a voz está instalada.

**No desktop**, com FFmpeg instalado e uma voz em português no sistema, `Gerar vídeo narrado` cria slides com narração e exporta MP4:
- **Windows:** usa `System.Speech` via PowerShell e requer uma voz pt-BR/pt-PT instalada em Configurações de Fala. Não instala vozes automaticamente.
- **Linux:** instale `espeak-ng` para disponibilizar narração `pt-br`. O Linux usa a voz sintética do sistema (qualidade inferior a modelos neurais como Kokoro).
- O áudio da cena é limitado à duração configurada; ajuste a duração para evitar cortar a fala. A exportação preserva o roteiro em seu próprio projeto.
- **Site (GitHub Pages):** por enquanto apenas organiza o roteiro e permite ouvir uma prévia da narração. O site **ainda não incorpora essa voz ao MP4 exportado**. Sem backend, `speechSynthesis` não permite capturar diretamente o áudio gerado.

Este passo prepara a infraestrutura compartilhada para incorporar Kokoro/faster-whisper posteriormente, sem apresentar a prévia como exportação de narração.
