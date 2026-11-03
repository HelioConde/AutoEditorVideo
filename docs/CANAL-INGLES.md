# Otaku Archives — segundo canal em inglês

Objetivo: abrir um canal internacional separado do Arquivo Otaku (PT-BR),
reaproveitando os mesmos materiais visuais aprovados, sem pagar por novas
imagens nem substituir arquivos dos Shorts originais.

**Importante:** nenhum canal YouTube é criado automaticamente por estes
scripts. É preciso criá-lo no YouTube e fornecer o ID verdadeiro.
Nenhum upload é feito durante a renderização nem no modo de prévia.

## 1. Criar o segundo canal (manual)

1. Entre em https://www.youtube.com/channel_switcher
2. Selecione **Criar um novo canal** e use um nome distinto, por exemplo
   **Otaku Archives** (nome e @handle devem estar disponíveis).
3. Configure país, idioma inglês, descrição e identidade visual na página
   do canal. Uma opção de descrição:
   "Anime mysteries, character analysis, mind games, and hidden details.
   Original English commentary with cinematic illustrations and storytelling.
   New anime Shorts exploring Death Note and more."
4. No YouTube Studio do segundo canal, abra
   Configurações > Canal > Configurações avançadas para obter o **ID do canal**
   (formato UC + 22 caracteres). Guarde esse ID localmente em
   .secrets/youtube-en-channel-id.txt (somente o ID, uma linha).
5. Não troque as configurações do canal brasileiro para inglês.
   Os canais são identidades separadas dentro da mesma Conta Google.

Referencia oficial: https://support.google.com/youtube/answer/1646861

## 2. Renderizar os Shorts em inglês

No PowerShell, a partir do projeto:

    cd "C:\Users\helio\Documents\arquivo-otaku-github"
    git pull --ff-only origin main

    # Planejar, sem consumir IA ou fazer upload
    .\gerar-shorts-en.ps1 -Acao planejar

    # Gerar dublagem EN de todos os cinco sem modificar as imagens
    .\gerar-shorts-en.ps1 -Acao voz

    # Renderizar os cinco MP4s com voz e legendas em inglês + capas
    .\gerar-shorts-en.ps1 -Acao renderizar

    # Refazer apenas um episódio, se necessário
    .\gerar-shorts-en.ps1 -Acao renderizar -Id 003-death-note-xadrez -Refazer

O projeto requer Python .venv com edge-tts, ffmpeg/ffprobe, Node.js e
motion-remotion/node_modules. As artes e layers original PT são reutilizadas
pelo Remotion, mas cada vídeo EN tem seu próprio áudio e timeline de legendas.

Arquivos finais:

    assets/gerados/shorts-animados/003-death-note-xadrez/en-US/
        003-death-note-xadrez-en-US-master-multicenas-personagens-v3-equilibrado.mp4
        003-death-note-xadrez-en-US-master-capa.jpg
        voz-master.mp3
        legendas.ass
        metadata-en.json
        qa-en-US.json

O mesmo padrão se aplica aos episódios 004, 005, 006 e 007.
A narração usa a voz en-US-GuyNeural com marcações reais de palavras.
Revisar qualidade editorial/linguística, pronúncia, grafia e sincronização
antes de enviar. English scripts ficam em conteudos/testes-animados-5-en.json.

Se a cena em português tiver legendas **dentro da imagem original**, será
necessário revisar/remover esse texto no asset antes de usar a versão EN.
As legendas geradas pelo Remotion são separadas e serão renderizadas em inglês.

## 3. Conectar o canal correto ao OAuth

O publicador usa as mesmas credenciais OAuth do projeto Google Cloud, mas
guarda um **token diferente** para o canal EN:

    .secrets/youtube-oauth-client.json        (cliente OAuth existente)
    .secrets/youtube-en-channel-id.txt       (ID do novo canal)
    .secrets/youtube-en-token.json            (token novo separado)

O arquivo youtube-token.json original PT-BR NUNCA é usado nem alterado.

Configurar o segundo ID localmente:

    New-Item -ItemType Directory -Force ".\.secrets" | Out-Null
    Set-Content -Path ".\.secrets\youtube-en-channel-id.txt" -Value "UC_COLE_AQUI_O_ID_REAL" -Encoding ASCII

Substitua pelo ID real retornado no Studio antes de executar.
O script exige que o canal selecionado na autorização Google seja o mesmo
Channel ID configurado. Caso contrário, ABORTA ANTES de qualquer upload.
Se tiver autorizado a conta errada, apague apenas
.secrets/youtube-en-token.json e reconecte.

    .\publicar-shorts-en.ps1 -Acao verificar -Limite 5
    .\publicar-shorts-en.ps1 -Acao conectar

## 4. Enviar apenas após revisão

Primeiro teste: **um vídeo privado**, sem risco de publicar errado:

    .\publicar-shorts-en.ps1 -Acao enviar -Id 003-death-note-xadrez -Privacidade private -ConfirmarEnvio

Depois, quando tiver verificado no Studio que a conta é o canal EN:

    .\publicar-shorts-en.ps1 -Acao enviar -Limite 5 -Privacidade private -ConfirmarEnvio

Arquivos já enviados são ignorados pelo hash SHA-256.
O estado separado fica em:

    assets/gerados/publicacao-youtube-en/estado.json

A publicação pública é uma escolha explícita:

    .\publicar-shorts-en.ps1 -Acao enviar -Id 004-death-note-segundo-kira -Privacidade public -ConfirmarEnvio

**Nota:** se um arquivo já estiver no histórico como privado, executar
com "public" NÃO muda seu status. Ajuste privacidade no YouTube Studio;
o bloqueio de duplicatas foi feito de propósito.

As capas estão em JPG local. Dependendo das permissões e limites da API,
o YouTube pode exigir ajuste manual da miniatura do Short no Studio.
Não tente repetir uploads de vídeos por causa de falha de miniatura.

## 5. Estratégia, conteúdo reutilizado e direitos

- Inglês de verdade: roteiro reescrito para fluidez, narração EN,
  legendas EN, capas EN, metadados EN e identidade própria do canal.
- Não publicar os mesmos arquivos com áudio em português no canal inglês.
- Separar cronograma, Analytics e títulos, começando com 1 Short de teste.
- Revisar direitos autorais e originalidade: mudança de idioma por si só
  não garante monetização. O YouTube avalia autenticidade, conteúdo repetitivo,
  propriedade intelectual e contribuição criativa.

Também é possível usar o recurso multilíngue do YouTube no canal existente,
se sua conta tiver acesso a essas ferramentas.

Referências oficiais:
- https://support.google.com/youtube/answer/1646861
- https://support.google.com/youtube/answer/13338784
- https://support.google.com/youtube/answer/1311392
- https://developers.google.com/youtube/data/reference/rest/v3/videos/insert
