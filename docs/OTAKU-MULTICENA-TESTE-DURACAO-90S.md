# Otaku Multicena — Experimento de Shorts com 1 minuto e 30 segundos

**Estado em 06/11/2026:** configuração editorial e validação offline. **Geração de imagens, voz, MP4 e uploads estão pausados.**

## O que mudou

- **Os 50 animes únicos** do catálogo V4 receberam o perfil de duração `short_90s_test`, alvo de **01:30 (90 segundos)** e tolerância técnica de **87 a 93 segundos**.
- O arquivo `conteudos/otaku-multicena-teste-90s-v1.json` contém **50 perfis editoriais**, mas **apenas os cinco primeiros** possuem roteiros originais completos de teste. Os 45 restantes são pautas e **não** devem ser tratados como roteiros prontos.
- Os cinco roteiros foram reescritos com narrativas específicas e fontes para conferência: Death Note (222 palavras), Steel Ball Run (220), Demon Slayer (223), Blue Box (221) e The Apothecary Diaries (217). Os 45 restantes ainda não têm roteiros.
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
6. 81–90s: **entregar a resposta ou a consequência concreta da história**, com a última frase terminando em ponto final. **Sem perguntas finais, pedidos de inscrição, curtida, comentário, compartilhamento ou convite para o próximo vídeo.**

### Novo padrão de encerramento — resultado, sem convite

Nos cinco roteiros-piloto, a seção final agora se chama `resultado`, não `fechamento`, e a narrativa prepara essa conclusão. Nos outros 45 animes, o mesmo contrato já foi configurado, mas as histórias completas ainda não foram escritas.

- A narração deve soar natural e direta, sem tom de propaganda ou aumento artificial de volume.
- A pergunta inicial deve ser resolvida por uma conclusão específica e verificável. Uma última pergunta retórica ou pedido de engajamento **não conta como resultado**.
- **Proibidos ao final:** “inscreva-se”, “curta”, “deixe o like”, “comente”, “compartilhe”, “siga”, “e você?”, “veja a parte 2”, slogan do canal ou voz pedindo uma ação.
- Última frase curta, com ponto final e sem alongar o vídeo em silêncio. O tempo de 90 segundos continua condicionado à medição de TTS real.
- Comparar o novo fechamento com vídeos anteriores nas mesmas primeiras 48 horas, sem atribuir mudança de retenção exclusivamente à ausência de CTA.

**Novos roteiros-piloto revisados:**
Death Note encerra explicando a estratégia de Light perto de L; Steel Ball Run encerra com a motivação de Johnny; Demon Slayer encerra com o princípio de Rengoku; Blue Box esclarece por que Chinatsu ficou na casa de Taiki; The Apothecary Diaries conclui com a consequência da curiosidade de Maomao. Todos continuam sujeitos a checagem factual e revisão da narração.

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

## Planejamento editorial V5 — 9/10 como meta de preparação, não garantia

A auditoria `scripts/otaku_multicena_editorial_score_v5.py` valida dez critérios. Os primeiros nove são de planejamento: gancho curto e específico; alegações de cânone ligadas a URLs de consulta; estrutura com seis etapas e cerca de 190–225 palavras; quatro descobertas ao longo dos 90 segundos; conclusão direta sem CTA; dez tomadas com instruções originais; direção da narração e pronúncia; bloqueios de direitos e spoilers; e teste comparativo de 40s versus 90s sem repetir os vídeos.

**O décimo critério não pode ser aprovado offline:** exige locução real de 87–93 segundos, vídeo renderizado e assistido, revisão factual humana, checagem visual e direitos de áudio/imagem. Portanto, atingir 9/10 aqui não significa que o vídeo esteja pronto, nem previsão de alcance ou retenção.

Para cada um dos cinco pilotos:
- Quatro descobertas previstas em aproximadamente 15, 31, 51 e 70 segundos. Esses tempos são editoriais; ajustar pelo TTS real.
- O encerramento do segundo 81 ao 90 apresenta a resposta, sem chamada para curtir, se inscrever ou comentar.
- Pelo menos dez tomadas planejadas, mas **nenhuma imagem/pose é declarada produzida**.
- Fontes externas do cânone são **pistas para verificação pelo editor**, não licença para usar capturas, música oficial nem garantia de fidelidade.
- A comparação de duração exige um controle **novo, com 40 segundos e também sem CTA**, de tópico comparável, mas roteiro e cenas diferentes para evitar duplicação. A duração é a variável principal; não utilizar vídeos antigos com CTA como se fossem controle igual.
- Antes de qualquer decisão sobre o novo formato, comparar taxa de continuidade no feed, segundos assistidos, percentual assistido, inscrições por mil e alcance após as primeiras 48 horas de cada vídeo.

Os roteiros de Death Note agora diferenciam expressamente a época em que Light conhecia o caderno e aquela em que ele perdeu as memórias. Maomao passa a investigar o caso específico do pó facial venenoso. Fontes para conferência: [Death Note — episódios na HBO Max](https://www.hbomax.com/br/pt/show/fabd8a3d-dd29-4f94-bc46-55941b14eacf); [The Apothecary Diaries E1](https://www.crunchyroll.com/pt-br/watch/GMKUXQ2VM/maomao); [Steel Ball Run — site oficial](https://jojo-portal.com/anime/sbr/story/); [Demon Slayer — Trem Infinito](https://demonslayer-anime.com/mugentrainarc/story/?id=ep5); [Blue Box — Netflix](https://media.netflix.com/en/only-on-netflix/81663323).

**Status:** geração e publicação continuam bloqueadas. Nenhum arquivo antigo, reserva, Short público ou comprovante foi substituído. Os cinco roteiros são rascunhos, não publicações aprovadas.
