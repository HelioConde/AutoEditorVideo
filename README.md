# AutoEditor Studio 2.0 — MVP local

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
