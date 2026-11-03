# Um comando: criar e publicar Shorts com voz, capa e descricao correta

## O que esta pronto

O comando principal gera videos originais do Arquivo Otaku, com:
roteiro cadastrado, narracao em PT-BR, legendas sincronizadas, imagens IA,
animacao Remotion, capa cinematografica 9:16 e metadados UTF-8 especificos
do episodio. A geracao respeita o teto editorial de 60 segundos.

Foram cadastrados os recaps de Death Note:
- 101-death-note-ep01: nascimento de Kira e aparicao de Ryuk
- 102-death-note-ep02: armadilha de L e Lind L. Tailor
- 103-death-note-ep03: investigacao, vigilância e oferta dos olhos de shinigami

Cada roteiro tem gancho inicial e chamada de inscricao no final. Os outros
cinco Shorts 003 a 007 continuam disponiveis e seus caches foram preservados.

## O unico comando (Windows PowerShell)

Dentro de C:\Users\helio\Documents\arquivo-otaku-github :

    git pull --ff-only origin main

    # Gerar e publicar o primeiro episodio como PUBLICO (acao explicita)
    .\criar-publicar-short.ps1 -Id 101-death-note-ep01 -Publicar -Privacidade public

    # Segundo e terceiro
    .\criar-publicar-short.ps1 -Id 102-death-note-ep02 -Publicar -Privacidade public
    .\criar-publicar-short.ps1 -Id 103-death-note-ep03 -Publicar -Privacidade public

A chave OAuth deve existir em .secrets/youtube-oauth-client.json; o token do
canal brasileiro e armazenado pelo publicador anterior em
.secrets/youtube-token.json. Confirme que essa conta corresponde ao canal
Arquivo Otaku ANTES do primeiro envio. Sem OAuth, o fluxo para antes de gastar
cota de IA. Ele nao usa o token do canal ingles.

## Modos seguros

    # Gerar sem publicar, para testar antes
    .\criar-publicar-short.ps1 -Id 101-death-note-ep01

    # Reutilizar somente cache, sem gastar nenhuma chamada nova de imagens
    .\criar-publicar-short.ps1 -Id 101-death-note-ep01 -MaxChamadas 0

    # Reaproveitar cache e refazer o MP4 local (nao publicar)
    .\criar-publicar-short.ps1 -Id 101-death-note-ep01 -MaxChamadas 0 -Refazer

    # Validar MP4 ja produzido sem rede, TTS, imagem, nem upload
    .\criar-publicar-short.ps1 -Id 101-death-note-ep01 -SomenteValidar

    # Publicar apenas em privado para conferir primeiro
    .\criar-publicar-short.ps1 -Id 101-death-note-ep01 -Publicar -Privacidade private

Opcoes: -Modelo gpt-image-1.5/gpt-image-2, -Perfil equilibrado/vivo/ultrassutil,
-MaxChamadas 0..180 (padrao 45), -Tentativas 1..3 (padrao 2).

## Como o sistema trata erros de geracao

- Gera e valida voz sincronizada; TTS transitorio pode receber 2 tentativas.
- Planeja cenas e calcula chamadas ainda pendentes antes de gastar cota.
- Reutiliza as respostas IA e camadas ja geradas em cache para cada cena.
- Se uma cena falhar, registra o erro, segue para as demais e tenta recuperar
  a cena com o cache. Nao tenta burlar limites do provedor.
- Se faltar qualquer imagem, se o QA reprovar uma cena, se a voz falhar, ou
  se o MP4 ultrapassar 60s, **NAO PUBLICA**.
- Se a renderizacao falhar, tenta novamente usando os arquivos locais.
- Preserva imagens e arquivos anteriores; o comando pode ser repetido.

O argumento -MaxChamadas e a cota maxima estimada de chamadas ainda
necessarias. API pode cobrar por tentativa que falhou sem gerar cache;
os logs mostram tentativas e o saldo conservador. Nao e possivel conhecer
a cobranca real de todas as chamadas a partir dos arquivos locais.

## Metadados, capas e envios

O JSON de descricao, titulo, serie e texto de capa de cada episodio fica em:

    assets/gerados/publicacao-youtube/episodios/<ID>.json

O MP4, voz, imagens e a capa final ficam em:

    assets/gerados/shorts-animados/<ID>/
        <ID>-master-multicenas-personagens-v3-equilibrado.mp4
        <ID>-master-capa.jpg
        voz-master.mp3
        legendas.ass

O comando passa explicitamente ao publicador o MP4, o JSON e a JPG daquele
mesmo episodio, com -Refazer para atualizar metadados de preparacao. O upload
salva o ID retornado pela API, com historico SHA-256; um arquivo ja enviado
nao sera enviado uma segunda vez.

**Limite real do YouTube Shorts**: embora o arquivo de capa JPEG seja criado
corretamente, a API pode recusar a miniatura personalizada (ex. HTTP 429).
Nessa situacao o sistema confirma o video, preserva a JPG e avisa que a capa
precisa ser ajustada pelo app YouTube caso a opcao esteja disponivel.
Nenhum codigo consegue garantir que o YouTube aceite uma capa de Short
quando a API recusa. Nao republique so para trocar miniatura.

## Seguranca e direitos

- Nunca publicar sem -Publicar explicito, por padrao privacidade private.
- Nunca ignorar limites de 60s, QA de imagem, autenticacao ou integridade.
- Nunca retentar automaticamente um upload cujo resultado remoto seja incerto.
- Nao usar screenshots, audio ou video retirado do anime: imagens de IA
  sao obrigatorias, com roteiro/narracao/edicao originais.
- Personagens e historias de anime ainda podem ser protegidos por direitos
  autorais; uso de IA nao garante elegibilidade para monetizacao.

O codigo do fluxo: scripts/fluxo_unico_short.py
O comando Windows: criar-publicar-short.ps1
Regras: AGENTS.md
Testes: tests/test_fluxo_unico_short.py
