# Motor opcional Remotion no Arquivo Otaku

O renderizador usa [Remotion](https://www.remotion.dev/) para movimento de personagem,
objetos e camera por quadros. Ele nao solicita imagens nem faz upload ao YouTube.

## Pre-requisitos no Windows

- Node.js 20 ou mais recente, npm e FFprobe;
- Python virtualenv com Pillow e numpy;
- No diretorio assets/gerados/shorts-animados/<ID>/:
  - background-*.png, character-*.png, object-*.png;
  - extra_object-*.png se for xadrez;
  - voz-*.mp3 e legendas.ass (gerados pelo fluxo anterior).

Os foregrounds precisam ser PNG com **alpha real** e sem verde contaminando
pele, cabelo ou bordas. A preparacao valida e recusa arte duvidosa.
Ela recorta as margens transparentes sem destruir as cores.

## Instalar o motor

Abra o PowerShell na raiz do projeto:

```powershell
uv pip install --python .\.venv\Scripts\python.exe "Pillow>=10,<13" "numpy>=1.24,<3"
cd .\motion-remotion
npm.cmd install
cd ..
```

## Preparar e renderizar o xadrez

```powershell
.\.venv\Scripts\python.exe .\scripts\renderizar_com_remotion.py --id 003-death-note-xadrez
.\.venv\Scripts\python.exe .\scripts\renderizar_com_remotion.py --id 003-death-note-xadrez --renderizar
```

Saida: `assets/gerados/shorts-animados/003-death-note-xadrez/003-death-note-xadrez-remotion.mp4`.

Demais IDs: 004-death-note-segundo-kira, 005-death-note-sangue,
006-death-note-shinigami e 007-death-note-maca.

O motor **reaproveita a voz e as legendas ASS** ja produzidas. Nao escreve
por cima do MP4 anterior. A miniatura continua gerada pelo fluxo anterior.

## Efeitos atuais

- Xadrez: duas pecas deslizam uma unica vez e param, sem deslizar eternamente.
- Misa: surge com opacidade e leve aproximacao.
- Sangue: gota estilizada com aceleracao vertical.
- Ryuk: flutua devagar, com pena se deslocando.
- Maca: cai, quica e se estabiliza.

Nao ha articulacao de dedos, boca, bracos ou pernas; para isso o projeto
[Rigby2D](https://github.com/jaisurya-dev-art/rigby2d) requer personagem
preparado em PSD com partes separadas.

## Integracao com a geracao de imagens

A funcao `request_image()` aceita os novos parametros
`background="transparent"` e `output_format="png"`.
Isso **somente pede** transparencia ao proxy. Se o proxy retornar imagem
opaca ou rejeitar o parametro, o fluxo deve parar, preservar `raw-*.png`
e avisar o usuario; nunca trocar por fundo verde silenciosamente.

O gerador local de cinco Shorts incluído nos ZIPs anteriores **ainda nao
constava neste repositorio**. O arquivo `conteudos/testes-animados-5.json`
foi versionado, e o novo motor consegue ler o cache local criado por ele.
Para produzir novas imagens no Windows, instale a atualizacao de cinco Shorts
com transparencia nativa disponibilizada no chat.

## QA e limites

Os testes no GitHub validam Python e o formato dos assets, sem gastar cota.
O compositor Remotion ainda precisa de uma primeira renderizacao no Windows
com npm instalado para aprovacao visual. Nao foi testado com sua conta/proxy.

Remotion tem licenciamento proprio: https://www.remotion.dev/docs/license/pricing
Revise os termos antes de distribuir a aplicacao como SaaS ou crescer equipe.
