# Melhorias de seleção automática — áudio + imagem (2ª etapa)

O modo desktop pode analisar um vídeo **localmente** para enriquecer o ranking de Shorts por transcrição:

- **FFmpeg / áudio:** decodifica em 16 kHz mono e calcula RMS por janela de aproximadamente 1 segundo. Um pico só conta quando supera em pelo menos 5 dB a mediana do próprio vídeo. Isso mede intensidade relativa, **não emoção**.
- **FFmpeg / imagem:** amostra a 2 FPS, redimensiona para largura 160px e utiliza o detector de diferenças de cenas do filtro \`select=gt(scene\\,0.25)\`. O resultado representa possíveis **cortes visuais**, não identifica gols, vitórias, reações ou pessoas.
- **Motor híbrido:** combina a pontuação textual existente com bônus limitados para picos de volume e transições visuais. Perfis **podcast**, **gameplay** e **tutorial** ajustam os bônus. Mostra evidências por candidato.
- **Fallback:** se a análise não estiver disponível, continua oferecendo a classificação por texto. A geração de Shorts continua passando por revisão e FFmpeg.
- **Privacidade:** FFmpeg executado no computador do usuário; não há upload do vídeo, chamada a IA remota, modelo extra ou necessidade de CUDA.

O usuário abre um projeto com mídia e SRT/transcrição, escolhe o perfil e clica em **Encontrar melhores momentos**. O desktop solicita \`GET /api/projects/:id/signals\`, cacheado por vídeo importado, e exibe o total de amostras de áudio e de cortes detectados. O endpoint \`POST /api/projects/:id/shorts\` considera os mesmos sinais cacheados, sem aceitar valores arbitrários enviados pelo navegador.

**Limites:** fase experimental aceita mídias até **10 min** de duração na análise audiovisual. Os comandos não usam shell e têm tempo limite por processo. Para mídia sem faixa de áudio, o vídeo pode fornecer apenas cortes de cena. A seleção ainda requer legendas, pois o ranking semântico não oferece candidates para vídeos silenciosos. Cortes e legendas respeitam os limites existentes. 

**Próximas fases recomendadas:** VAD (Silero), PySceneDetect opcional para cortes robustos, alinhamento de palavras, identificação de faces com YuNet/MediaPipe e avaliação semântica contextual local. Não declarar essas ferramentas como integradas antes de testes reais.

## Revisão e aprovação explícita dos candidatos

Na interface de Shorts, cada candidato tem um checkbox para incluir/excluir da exportação. O usuário pode ouvir o momento e ajustar um corte na timeline; a seleção do lote não altera os timestamps originais. O frontend envia `selectedRanges` e o backend valida cada par `start/end` contra os **três candidatos ranqueados novamente**, rejeitando mudanças ou duplicatas. O servidor continua gerando arquivos separados e legendados apenas para os aprovados.

A compatibilidade com chamadas antigas é mantida: sem `selectedRanges`, o servidor gera os primeiros candidatos, respeitando `count`. Com seleção explícita, o novo app solicita até três candidatos e limita a saída aos marcados.

Teste Playwright: simula gravação com duas cenas de cores distintas e áudio real; verifica presença positiva de amostras de áudio e mudanças de cena, alternância das caixas de aprovação e geração de Short vertical.

## Detecção de movimento para vídeos sem transcrição

Além de RMS e mudanças de cena, o analisador mede `signalstats.YDIF` a 2 quadros/s no FFmpeg. O campo `motion` contém pares `{time,value}` sem imagens ou dados binários. O módulo `src/visual-highlights.js` usa janelas de 12 a 18 segundos e descarta candidatas com poucas amostras ou atividade visual insuficiente. Duração máxima da análise: 10 minutos.

Com transcrição, mantém-se o ranking por falas com evidência adicional de movimento; sem transcrição, o programa usa a trilha de movimento e exporta **Shorts sem legendas**. A análise não interpreta semanticamente o que aconteceu na cena. Todos os candidatos passam pela revisão do usuário e pela validação de intervalos no servidor antes de exportar. Para detecção de ações específicas (gols, kills, reações), ainda será necessário um modelo de visão adaptado ao tipo de conteúdo.

## Etapa adicional: margens de silêncio e coerência textual

Na mesma passada de RMS, o FFmpeg executa `silencedetect=noise=-32dB:d=0.25`; apenas intervalos completos entram em `signals.silences`. O ranqueamento considera conectivos e pontuação final quando o áudio foi analisado e o editor pode ampliar em até 0,45s os limites dentro de pausas, mas nunca remover partes das legendas escolhidas, invadir falas vizinhas ou exceder a duração máxima de 45s. Sem intervalos confiáveis, os limites originais da transcrição são mantidos. Não equivale a WhisperX, VAD Silero, diarização ou análise semântica por modelo multimodal.

## Relevância temporal dos acontecimentos (evolução do ranking visual)

Para gameplays e vídeos sem fala, o ranking agora detecta **picos sustentados de movimento em relação à atividade típica do próprio vídeo**, usando as amostras YDIF já calculadas pelo FFmpeg. O detector agrupa quadros próximos e só considera eventos com pelo menos duas amostras elevadas; flashes isolados não recebem bônus. As janelas de Short também podem começar antes desses picos, preservando um pouco do contexto anterior.

A pontuação reduz a influência do movimento médio contínuo e concede um bônus limitado a picos visuais e acústicos, sem confundir movimento com emoção ou qualidade editorial. O candidato exibe quantos picos sustentados contribuíram para sua seleção. Vídeos com movimento uniforme continuam elegíveis, mas não ganham pontos fictícios por acontecimentos não detectados.

Os testes em `tests/unit/visual-highlights.test.mjs` cobrem cenas estáticas, movimento contínuo, flash de um único quadro e dois acontecimentos visuais separados. A análise permanece 100% local e os limites de duração existentes não mudam.
