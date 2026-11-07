# Otaku Multicena — Experimento de Shorts com 1 minuto e 30 segundos

**Estado em 06/11/2026:** configuração editorial e validação offline. **Geração de imagens, voz, MP4 e uploads estão pausados.**

## O que mudou

- **Os 50 animes únicos** do catálogo V4 receberam o perfil de duração `short_90s_test`, alvo de **01:30 (90 segundos)** e tolerância técnica de **87 a 93 segundos**.
- O arquivo `conteudos/otaku-multicena-teste-90s-v1.json` contém **50 perfis editoriais**, mas **apenas os cinco primeiros** possuem roteiros originais completos de teste. Os 45 restantes são pautas e **não** devem ser tratados como roteiros prontos.
- Os cinco roteiros foram elaborados para a duração-alvo: Death Note (203 palavras), JoJo: Steel Ball Run (215), Demon Slayer (212), Blue Box (207) e The Apothecary Diaries (207).
- O gancho falado foi reduzido para cerca de **5–7 palavras**, pensando numa abertura de 1–3 segundos, sem perder contexto.
- O tempo real **só é confirmado com o arquivo de áudio do TTS**; 200 palavras por si só não garantem 90 segundos. Não acelerar a narração demais nem inserir silêncios artificiais para forçar a meta.
- O planejamento visual sugere **10 tomadas distintas**, com marcos aproximados em 0, 4, 12, 19, 29, 40, 50, 61, 71, 81 e 90 segundos. Os cortes efetivos devem respeitar as marcações reais das palavras e as ações da cena.
- O validador V3 e o QA de MP4 aceitam agora **90 segundos somente quando o perfil de teste for explicitamente selecionado**. Fluxos antigos de 20–60 segundos continuam com o contrato anterior.

## Proteção contra bloqueio por Content ID

O YouTube aceita Shorts verticais de até três minutos, mas **Shorts com mais de um minuto e reivindicação ativa de Content ID de qualquer tipo podem ser bloqueados globalmente**. Por isso, usar trilhas e outros materiais autorizados, manter comprovantes de licença e revisar o vídeo antes de qualquer envio.

Fontes oficiais:
- https://support.google.com/youtube/answer/15424877
- https://support.google.com/youtube/answer/6013276

**Não usar OST oficial de anime, trechos originais, cenas copiadas ou músicas de terceiros sem direitos verificados.** O fato de uma imagem ter sido gerada por IA não garante que seu uso seja livre de questões de direitos autorais.

## Plano de comparação de duração

O objetivo é **testar**, e não presumir, se 90 segundos oferece melhor resultado do que o formato atual:

| Grupo | Formato | Experimento |
|---|---|---|
| Controle | 35–45 segundos | Mantém a dinâmica curta de mistério/revelação |
| Teste | 87–93 segundos | Desenvolvimento emocional e narrativa com mais contexto |

Para comparar, usar cinco temas parecidos em cada grupo; medir **cada Short exatamente nas suas primeiras 48 horas**, sem confundir diferença de idade com desempenho. Priorizar:
- taxa de espectadores que escolheram assistir em vez de deslizar;
- tempo médio de visualização **em segundos** e porcentagem média assistida **separadamente**;
- views e exposições no feed nas primeiras 48h;
- inscritos por mil visualizações e compartilhamentos por mil visualizações.

**Não interpretar os resultados de cinco vídeos como demonstração causal.** Se 90s perder retenção percentual mas ganhar tempo médio absoluto, avaliar também os inscritos e o engajamento antes de escolher a duração principal.

## Organização da história 90 segundos

1. 00–04s: gancho rápido e claro, sem saudação ou introdução.
2. 04–19s: contexto útil e promessa que será cumprida.
3. 19–40s: detalhe surpreendente e risco.
4. 40–61s: conflito, contraintuição ou ponto de virada.
5. 61–81s: explicação concreta / recompensa emocional da pergunta inicial.
6. 81–90s: encerramento breve e CTA contextual, sem alongar o vídeo à força.

**10 tomadas** são uma referência, não uma obrigação cega de cortar a cada X segundos. Adicionar ângulos e poses reais quando necessário, com arte original e qualidade revisada.

## Verificação offline, sem geração de mídia

No projeto (Python):

```powershell
python scripts/otaku_multicena_duration_90.py --output reports/otaku-duracao-90-v1.json

# Executar só quando uma narração real e legalmente autorizada já existir:
python scripts/otaku_multicena_duration_90.py --rank 1 --audio "caminho/voz-master.mp3"

# Depois de renderizar uma prévia real, verificar MP4:
python scripts/otaku_multicena_video_qa.py --duration-profile short_90s_test --video "caminho/preview.mp4"
```

Manifesto V3 de um vídeo de 90s precisa declarar `duration_profile: "short_90s_test"` e `duration_frames` baseado na duração medida, em 30 FPS. Um áudio de 86 ou 95 segundos **não deve ser falsamente aprovado**: reescrever e regravar ou revisar ritmo natural antes de aprovar.

O planejamento dos cinco primeiros roteiros está no JSON; sua correção factual, spoilers, tom e qualidade audiovisual ainda **precisam de revisão humana**.

## O que permanece bloqueado

- Nenhuma alteração em Shorts publicados, IDs, comprovantes e na fila original 50 → 1.
- Nenhuma criação de MP3, MP4 ou PNG, ou upload para o YouTube foi autorizada por esta atualização.
- Os 45 roteiros completos restantes **não foram escritos** nesta etapa — apenas receberam o perfil de 90s para planejamento.
- `pause_requested=true`, `authorized_public=false`, `maintenance_complete=false` e `resume_authorized_after_maintenance=false` permanecem intactos.

A conclusão desta etapa é **perfil de tempo e roteiros-piloto preparados**; a aprovação do formato 90s depende de narração medida, prévia real revisada e posterior avaliação de desempenho.
