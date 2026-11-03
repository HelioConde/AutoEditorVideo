# Experimento de Shorts no YouTube: um episódio por hora

## Objetivo

Comparar vídeos publicados com pelo menos 60 minutos de intervalo
em vez de um lote de vários Shorts em poucos minutos. Isto NÃO
comprova, por si só, que o algoritmo imponha uma cota diária: os
episódios têm roteiros diferentes, horários diferentes e audiências
potencialmente diferentes.

Neste momento, somente os recaps de Death Note EP02 e EP03 estão
cadastrados para a fila. O EP01 já foi publicado anteriormente
e NÃO será reenviado pelo teste.

## Comando único, publica de verdade

Abra o Windows PowerShell no computador onde estão o editor,
as credenciais OAuth do YouTube e os arquivos de mídia.

    cd "C:\Users\helio\Documents\arquivo-otaku-github"
    git pull --ff-only origin main
    .\publicar-recaps-por-hora.ps1 -Publicar -Privacidade public

Com esse comando:
1. Produz e publica o EP02 **se ainda não tiver sido publicado**.
2. Confirma o video_id e a data/hora de upload no registro local do MP4.
3. Aguarda até transcorrer pelo menos 60 minutos desde o envio real do EP02.
4. Produz e publica o EP03, guardando novamente o ID e o horário.
5. Encerra. Não publica vídeos sem roteiro ou cria episódios adicionais.

**IMPORTANTE:** o PowerShell deve permanecer aberto e o computador ligado.
O script faz uma espera local; não é uma tarefa remota ou automática do
ChatGPT. Se o computador dormir ou o processo for encerrado, execute de
novo. O sistema utiliza os registros locais para não duplicar os uploads
já confirmados e respeitar o último horário registrado.

Se o EP02 já foi enviado com o gerador padrão, a execução pula o
upload repetido e calcula o horário do EP03 a partir do registro original.

## Planejar sem enviar nem consumir cota de IA

    .\publicar-recaps-por-hora.ps1

O modo sem -Publicar mostra IDs e horários elegíveis, sem gerar
imagens, sem criar voz e sem autenticar no YouTube.

## Enviar somente o EP02 agora

    .\criar-publicar-short.ps1 -Id 102-death-note-ep02 -Publicar -Privacidade public

Quando quiser automatizar o próximo, execute o comando
publicar-recaps-por-hora.ps1 -Publicar. Ele deve reconhecer que o EP02
já foi publicado e aguardar até completar uma hora desde o upload
confirmado para enviar o EP03.

## Proteções

- Publicação explícita obrigatória com -Publicar; sem o parâmetro, prévia.
- Upload do mesmo MP4 não é repetido se o SHA-256 já tem ID confirmado.
- Se a produção de voz, imagens, MP4, capa ou OAuth falhar, para a fila.
- Nenhum Short pode ultrapassar 60 segundos (validação já existente).
- Nunca repete automaticamente um upload cuja confirmação seja ambígua.
- Exige a mesma privacidade do vídeo anterior, sem alterar publicações.
- Não tenta driblar bloqueios do YouTube ou cotas de imagem.
- O agendamento compara o fuso UTC dos registros, evitando erros de horário de verão.
- As mídias e os tokens continuam apenas no seu computador, não no GitHub.

O arquivo de vídeo e seu comprovante ficam respectivamente em:

    assets/gerados/shorts-animados/<ID>/<ID>-master-multicenas-personagens-v3-equilibrado.mp4
    assets/gerados/publicacao-youtube/estado-upload-<prefixo-sha256>.json

Se o vídeo estiver publicado no YouTube mas faltar o registro local,
confira o Studio ANTES de repetir o comando para não criar duplicatas.

## Métricas para comparar no YouTube Studio

Registre as visualizações, visualizações intencionais, "Mostrados no
feed", porcentagem que continuou assistindo, média de tempo assistido
e inscrições geradas por vídeo após 1h, 6h, 24h e 48h. Compare com
os Shorts antigos publicados em lotes. Não conclua que existe limite
diário apenas porque alguns vídeos começaram com zero views.

## Referências técnicas

- Orquestração: scripts/publicar_recap_hourly.py
- Comando do Windows: publicar-recaps-por-hora.ps1
- Criador e publicador original: criar-publicar-short.ps1
- Regressões offline: tests/test_publicar_recap_hourly.py
