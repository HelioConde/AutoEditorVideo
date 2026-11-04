# Biblioteca de videos — quatro canais + revisao no YouTube Studio

**Mudanca de fluxo decidida em 04/11/2026:** o criador avalia os aspectos
artisticos e narrativos do **video completo no YouTube Studio**, depois de
enviar o MP4 de revisao como **privado**. Nao exigir cliques por cena para
liberar renderizacao, capa ou montagem. **Nunca forjar aprovacao humana.**

Continuam obrigatorios os bloqueios tecnicos: ausencia de arquivos,
PNG/camadas invalidos, SHA divergente, falhas fatais de composicao,
video sem audio, duracao fora do limite do projeto, formato inadequado,
credenciais incorretas, IDs divergentes e imagens/cenas expressamente
reprovadas e ainda nao corrigidas. A conferencia de direitos/licencas e
das configuracoes para conteudo infantil tambem nao e opcional.
A revisao artistica posterior **nao significa** publicacao automatica.

## Pastas novas

Depois da primeira organizacao, no Explorer:

    C:\Users\helio\Documents\arquivo-otaku-github\assets\gerados\biblioteca-videos\
      Kids\
        kids-001-estrela-azul\
          final.mp4
      Gamer\
        game-001-minecraft-um-coracao\
          final.mp4
      Otaku Multicena\
        003-death-note-xadrez\
          003-death-note-xadrez-master-multicenas-personagens-v3-equilibrado.mp4
        arquivos-antigos\
          arquivo-otaku-piloto-v07-reuso.mp4
      Otaku Reframe\
        003-death-note-xadrez\
          003-death-note-xadrez-en-US-master-multicenas-personagens-v3-equilibrado.mp4
      catalogo.json

Os caminhos acima sao exemplos, e nao confirmacao de que esses MP4s
existem na maquina: o script encontra somente os arquivos presentes.

## Comandos Windows

    cd "C:\Users\helio\Documents\arquivo-otaku-github"
    git pull --ff-only origin main

    # Verificar onde os MP4s serao arquivados. Nao altera nada.
    .\organizar-videos.ps1 -Acao Prever

    # Criar as quatro pastas e fazer COPIAS verificadas.
    .\organizar-videos.ps1 -Acao Organizar

    # Abrir a biblioteca e uma pasta especifica no Explorador.
    .\organizar-videos.ps1 -Acao Abrir
    .\organizar-videos.ps1 -Acao Abrir -Canal "Otaku Reframe"
    .\organizar-videos.ps1 -Acao Abrir -Canal "Gamer"

    # Alternativa que poupa espaco em NTFS: links fisicos (nao backups).
    .\organizar-videos.ps1 -Acao Organizar -Metodo Link

O modo Copiar usa copia independente e nunca move nem apaga a origem.
O modo Link usa hardlink: dois nomes para os mesmos bytes, economiza
espaco, mas **editar um MP4 pelo atalho fisico modifica tambem o original**.
Nao e backup. Use Copiar se for editar os videos da biblioteca.

O catalogo JSON registra canal, episodio, arquivo original, arquivo
de destino, SHA-256 e tamanho. Se uma nova renderizacao tiver o mesmo
nome e conteudo diferente, a biblioteca guarda a nova versao com
sufixo de hash, sem destruir a anterior.

Fontes reconhecidas:
- assets/gerados/piloto-canais-v3/kids/<ID>/final.mp4 -> Kids.
- assets/gerados/piloto-canais-v3/games/<ID>/final.mp4 -> Gamer.
- assets/gerados/shorts-animados/<ID>/*.mp4 -> Otaku Multicena.
- assets/gerados/shorts-animados/<ID>/en-US/*-en-US-*.mp4 -> Otaku Reframe.
- assets/gerados/arquivo-otaku-*.mp4 -> Otaku Multicena / arquivos-antigos.

Nao copiar capturas separadas de jogos, videos de cenas, temporarios,
rascunhos, nem arquivos de origem incerta. Arquivos ambiguos aparecem
na lista de "unclassified" no relatorio, para verificacao humana.
Nenhuma fonte e reclassificada por suposicao de nome ou miniatura.

Depois que a biblioteca existir, renders concluídos dos motores
Remotion PT, EN e piloto Kids/Games a atualizam automaticamente.
Se a biblioteca nao existir, a producao continua normalmente. Falhas
ao arquivar sao avisos e **nao invalidam um MP4 ja concluido**.

## Render EN com revisao posterior

    # Origem do erro antigo: Cena 02 exigia aprovacao manual de multicamadas.
    # Isso nao e mais necessario, se todos os testes tecnicos passarem.
    .\canal-ingles.ps1 -Acao Renderizar -Id 003-death-note-xadrez

    # Inspecionar assinatura e metadados, sem enviar.
    .\canal-ingles.ps1 -Acao VerificarUpload -Id 003-death-note-xadrez

    # UPLOAD OPCIONAL privado para assistir e avaliar no YouTube Studio.
    # Exige conta Otaku Reframe correta, QA assinado e confirmacao especifica.
    .\canal-ingles.ps1 -Acao Enviar -Id 003-death-note-xadrez -ConfirmarEnvio

A opcao -ExigirMovimentoPersonagem continua **estrita e voluntaria**:
ela ainda podera bloquear uma cena que usa apenas zoom ou que nao tem
camadas moveis verificadas. Para revisar isso no video completo privado,
nao passe essa opcao ao renderizar. Nao chamar zoom de movimento de
personagem, e nao falsificar o relatorio de movimento.

No YouTube Studio, verificar audio e pronuncia, legendas, movimento
real das personagens, cortes, capa, continuidade e qualidade geral.
Se houver erro, produzir uma nova versao e conferir novamente o Studio.
Nao repetir upload automatico se houver falha ambigua da API; verificar
a conta antes. Para tornar publico, exigir confirmacao posterior.

**Nenhum upload ou reorganizacao local ocorre pelo simples commit no GitHub.**
O script organiza somente o que existe em seu computador, e os comandos
de upload sao separados e requerem confirmacao.
