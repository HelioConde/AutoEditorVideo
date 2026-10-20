# Versão web — AutoEditor Studio

## Endereço público
Depois que o GitHub Pages for ativado em **Settings → Pages → Build and deployment → Source: GitHub Actions**, o workflow de publicação deve disponibilizar o site em:

**https://helioconde.github.io/AutoEditorVideo/**

> Atenção: a existência do workflow não garante que o Pages esteja habilitado. Confirmar deployment verde em **Actions → Publish AutoEditor Studio Web to GitHub Pages** e testar a URL antes de anunciar publicamente.

## O que funciona sem servidor
- Importar **MP4/WebM até 30 MB**, com até **2 minutos**, diretamente no navegador.
- Assistir ao vídeo com os controles nativos e recortar trechos de **0,25 a 20 segundos**.
- Exportar MP4 H.264 + áudio AAC (quando presente) em **360 × 640 (9:16)** ou **640 × 360 (16:9)**, 24 FPS.
- Baixar arquivo com `download` do navegador.
- Ver estados de upload, erro, exportação e conclusão.

**Arquivos não são enviados para o GitHub, para o CDN ou para uma API.** A edição ocorre na memória do navegador, por meio de WebAssembly; fechar/recarregar perde o projeto. O navegador requisita o pacote FFmpeg de jsDelivr na primeira exportação e pode requisitar fontes Google. É necessária conexão na primeira exportação. Não é um serviço offline completo.

## Tecnologias e restrições
- `vite build --mode web` gera o HTML estático em `dist/`, com base `/AutoEditorVideo/`.
- `src/main.jsx` seleciona `WebApp.jsx` no modo `web`; no build desktop permanece `App.jsx`. O bundle Pages não usa as rotas `/api` do servidor Express.
- `@ffmpeg/ffmpeg@0.12.15` e `@ffmpeg/util@0.12.2` fazem o processo no navegador. O **core single-thread** `@ffmpeg/core@0.12.10` é carregado do CDN; por isso não requer `SharedArrayBuffer` ou configuração COOP/COEP não suportada pelo Pages.
- Renderização e codecs dependem do dispositivo e navegador. Em computadores lentos, pode demorar e consumir memória. Para arquivos maiores, utilize a edição desktop.
- FFmpeg.wasm possui as próprias exigências de licenciamento; revisar distribuição e dependências antes de vender/redistribuir.

## Desenvolvimento

```powershell
npm install
npm run dev:web
```

Abra **http://127.0.0.1:5174** (sem back-end). A edição desktop continua `npm run dev` em **http://127.0.0.1:5173**.

```powershell
npm run build:web
npm run test
npx playwright install chromium
npm run test:e2e:web
```

Opcional: com FFmpeg do sistema e internet disponíveis, `WEB_WASM_INTEGRATION=1 npm run test:e2e:web` valida a renderização real pelo motor WASM (definir a variável de ambiente de acordo com o shell).

## Publicação
- `.github/workflows/pages.yml`: em push em `main` ou por acionamento manual, gera `dist/`, envia Pages artifact e faz deploy oficial com `actions/deploy-pages`.
- **Habilitação inicial**, caso não esteja ativa: abrir `https://github.com/HelioConde/AutoEditorVideo/settings/pages` → Source → GitHub Actions.
- Para domínio personalizado, atualizar `vite.config.js` (`base`) e configuração do Pages.
- Nunca embutir tokens privados nos bundles web. A publicação é **estática** e não inclui armazenamento remoto ou API de terceiros para publicação em redes sociais.

## Roteiro
1. Validar funcionalidade no navegador Chrome/Edge Windows e Android.
2. Adicionar marcação de cortes em timeline real, miniaturas de quadros e download de legendas.
3. Investigar PWA/offline com hospedagem apropriada dos assets grandes.
4. Oferecer processamento remoto **apenas** em produto com backend autenticado e custo conhecido.

## Timeline e sequência

A edição web exibe 8 miniaturas reais extraídas no navegador, permite pré-visualizar o trecho e adicionar até cinco cortes. O arquivo final contém apenas os cortes adicionados, concatenados pela ordem escolhida, com duração acumulada de **até 20 segundos**. O motor WebAssembly renderiza os cortes individualmente, normaliza codecs e os une; esse modo usa mais memória e CPU do que a exportação de um único trecho. Limites do arquivo original permanecem 30 MB e 2 min.

## Compartilhamento de projetos e roteiro

`Exportar projeto` baixa `.autoeditor.json`; `Importar projeto` aplica cortes, proporção e cenas de outro dispositivo, sem salvar ou enviar a mídia. Ao importar um projeto com vídeo, selecione o mesmo nome de arquivo e a mesma duração; se a duração for diferente, os cortes são limpos.

O novo modo de roteiro cria e edita até seis cenas. A prévia de voz usa `window.speechSynthesis`; a voz não é capturada no MP4. A renderização narrada offline está disponível somente no desktop, usando a voz local do sistema. O GitHub Pages não fornece servidor de renderização, contas ou armazenamento.

## Novidades visuais (2.4 beta)
Tema visual e transição são propriedades portáteis de cada cena no manifesto v1. O editor aceita imagens de fundo até 2 MB, apenas para prévia local no site. **O site ainda não exporta vídeos narrados**, nem inclui fotos binárias no arquivo portátil. No desktop, a mesma imagem serve à composição dos slides narrados com FFmpeg. Alternativas: fade para preto entre cenas ou corte direto.
