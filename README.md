<div align="center">

<h1>🎬 AutoEditor Studio</h1>

<strong>Edite vídeos localmente e transforme gravações em Shorts com mais agilidade</strong>

<p>Importação, timeline, exportação e sugestões de trechos — sem depender de uma plataforma de edição por assinatura.</p>

<a href="https://helioconde.github.io/AutoEditorVideo/"><img alt="Web edition" src="https://img.shields.io/badge/Edi%C3%A7%C3%A3o-Web-2563eb?style=for-the-badge"></a>
<a href="https://github.com/HelioConde/AutoEditorVideo"><img alt="Desktop edition" src="https://img.shields.io/badge/Edi%C3%A7%C3%A3o-Local-15803d?style=for-the-badge"></a>

<p><a href="https://helioconde.github.io/AutoEditorVideo/"><strong>Abrir editor web</strong></a> · <a href="docs/WEB_EDITION.md"><strong>Guia da Web</strong></a> · <a href="docs/AUTO_SHORTS_MVP.md"><strong>Como funcionam os Shorts</strong></a></p>

</div>

---

## Por que este projeto existe?

O **AutoEditorVideo** começou como um experimento de edição automatizada e evoluiu para um estúdio de vídeo com **duas experiências**: edição local assistida por FFmpeg e uma edição web mais limitada, executada no próprio navegador.

A direção atual é facilitar a criação de **Shorts verticais a partir de vídeos maiores**. O editor oferece revisão humana dos cortes sugeridos; a escolha automática de trechos não deve ser confundida com inteligência capaz de prever viralização.

## Duas formas de editar

| Recurso | **Desktop / servidor local** | **Web / navegador** |
| --- | --- | --- |
| Processamento | Node.js + FFmpeg nativo | FFmpeg WebAssembly |
| Importar e visualizar | Sim | Sim, sujeito a limites menores |
| Cortar e exportar | Sim | Sim, sujeito à memória e desempenho do navegador |
| Transcrição e sugestões de Shorts | Fluxo experimental com Whisper.cpp local ou SRT | Não equivalente ao backend local completo |
| Instalação | Node.js 22+, FFmpeg e FFprobe | Acesso ao site e downloads iniciais do motor |
| Hospedagem | API somente local | GitHub Pages estático |

**Privacidade:** o processamento foi projetado para ocorrer localmente nas duas edições. Não exponha a API Node diretamente à internet: ela não possui autenticação para uso público multiusuário.

## Recursos em destaque

- **Projetos e arquivos:** importação de vídeo, prévia e armazenamento de rascunhos locais.
- **Timeline:** seleção de início/fim, cortes múltiplos, organização e exportação.
- **Formatos:** saída MP4 em proporções horizontal e vertical, conforme a edição.
- **Legendas e transcrição:** funcionalidades experimentais no ambiente local com configuração de ferramentas adicionais.
- **Shorts assistidos:** sugestões baseadas em sinais transparentes da transcrição e geração de trechos com revisão do editor.
- **QA:** testes Node, cenários Playwright, verificações de mídia e workflows de CI.

### Como funciona a seleção de Shorts

```text
Vídeo importado
      ↓
Transcrição Whisper.cpp local ou arquivo SRT
      ↓
Análise heurística de trechos e sugestões
      ↓
Você revisa, ajusta e escolhe
      ↓
Exportação em MP4 9:16 com legendas (quando configurado)
```

Os critérios da primeira implementação analisam texto, continuidade, perguntas e momentos de contraste. Há experimentos adicionais de análise visual e multimodal, mas **o ranqueamento não equivale a uma avaliação humana de interesse ou qualidade**.

[**Detalhes do MVP de Shorts**](docs/AUTO_SHORTS_MVP.md) · [**Ranking multimodal experimental**](docs/MULTIMODAL_RANKING.md)

## Início rápido

### Desktop com backend local

Instale **Node.js 22+** e configure **FFmpeg + FFprobe** no `PATH`. Depois:

```bash
git clone https://github.com/HelioConde/AutoEditorVideo.git
cd AutoEditorVideo
npm install
npm run dev
```

Abra `http://127.0.0.1:5173`. O comando também inicia a API local, normalmente na porta `3011`.

### Editor Web

```bash
npm install
npm run dev:web
```

Normalmente disponível em `http://127.0.0.1:5174`. Para gerar a versão estática, execute `npm run build:web`.

A Web pode exigir um download inicial do FFmpeg.wasm e limitações de tamanho e duração. Para detalhes de navegador e exportação, consulte [WEB_EDITION.md](docs/WEB_EDITION.md).

## Verificações

```bash
npm run check
npm run test:e2e
npm run test:e2e:web
npm run qa:media
```

O script `check` executa testes e builds; os outros comandos permitem validação de interface e cenários de mídia. E2E requer navegador Playwright instalado. **A presença de testes no projeto não é garantia de aprovação na máquina do usuário.**

## Arquitetura

```text
src/            Interface React/Vite e recursos de edição
server/         API Node e processamento local
scripts/        Scripts de desenvolvimento e QA
tests/          Testes de unidade e E2E
docs/           Regras de produto, design, Web e Shorts
legacy/         Implementação histórica preservada
```

A edição web é estática e **não executa o backend Node no GitHub Pages**. O desktop usa o FFmpeg instalado no computador e grava projetos/exports localmente. Para trabalho com vídeos grandes, reserve espaço livre e tempo de processamento.

## Estado do desenvolvimento

O editor possui um **MVP funcional em evolução**, com partes mais maduras (importação, corte, exportação) e recursos experimentais (transcrição, detecção de melhores momentos, ranking multimodal). Recomendamos revisar o resultado antes de publicar.

- [Editor web](https://helioconde.github.io/AutoEditorVideo/)
- [Documentação completa dos Shorts](docs/AUTO_SHORTS_MVP.md)
- [Sistema visual](docs/DESIGN_SYSTEM.md)
- [Auditoria de experiência](docs/UX_AUDIT_2026-10-20.md)
- [Histórico anterior do README](docs/README_HISTORY_2026-10-25.md)

---

<div align="center"><strong>Desenvolvido por <a href="https://github.com/HelioConde">Hélio Conde</a></strong></div>
