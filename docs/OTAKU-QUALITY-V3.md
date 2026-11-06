# AutoEditorVideo — Prévia de Qualidade V3

Status: implementação técnica disponível para elaboração de props de prévia. Geração de imagens, geração de MP4 e publicação no YouTube continuam PAUSADAS.

## Capacidades implementadas

- Planejamento de 8 a 12 tomadas com início ancorado nas palavras reais da narração (TTS).
- Validação de gancho inicial e resposta/revelação na segunda metade da história.
- Cenas distintas com hashes SHA-256 e evidência explícita de direitos.
- Suporte opt-in a animações reais de personagem em poses PNG RGBA transparentes: ao menos dois quadros diferentes, 1024x1536, 4 a 12 FPS, com fundo limpo declarado pelo autor.
- Uma cena sem poses é marcada como estática. Nunca atribuir animação articulada a simples movimentos de câmera.
- Trilha original ou licenciada em volume baixo (até 0,2) e efeitos pontuais (até 0,4).
- Auditoria técnica de MP4 existente: duração, 1080x1920, 30 FPS, áudio presente, níveis de som e alertas de trechos pretos/congelados.

## Arquivos

- scripts/otaku_multicena_quality_v3.py: monta props do Remotion com arquivos preexistentes, sem render.
- motion-remotion/src/master-short.tsx: suporta soundCues, backgroundMusic e rigFrames.
- scripts/otaku_multicena_video_qa.py: inspeção AV local com ffmpeg/ffprobe, sem publicar.
- tests/test_otaku_multicena_quality_v3.py: cenas e poses sintéticas com Pillow; sem IA ou YouTube.
- tests/test_otaku_multicena_video_qa.py: validações de vídeo simuladas; sem gerar mídia.
- .github/workflows/otaku-editorial-quality-offline.yml: testes e relatórios, sem segredos de provedores de imagem e YouTube.

## Especificação de uma cena V3

Em um manifesto JSON por episódio, incluir os campos obrigatórios:

- schema = autoeditorvideo/quality-preview/v3
- episode_id = identificador único (letras minúsculas, números e hífens)
- narration_script = texto idêntico às palavras da voz, na ordem
- voice = arquivo MP3 original e voice_rights com type e evidence
- sha256 = mapa do nome para SHA-256 de TODOS os arquivos utilizados
- manual_visual_review = false
- duration_frames = duração da voz em quadros, com 30 FPS
- hook_text = 2 a 9 palavras, encontradas na abertura da narração
- payoff_text = 2 a 9 palavras, encontradas na segunda metade
- shots = 8 a 12 entradas únicas, cada uma com start_phrase, background, shot_type, beat_role e rights (type/evidence)

Para animação de personagem real, a cena também deve conter pose_frames (2 a 12 PNGs transparentes), pose_fps (4–12) e clean_plate_confirmed = true. O renderizador só usa essas poses quando o manifesto passou no validador. O arquivo de fundo deve estar livre do personagem para não criar duplicação ou fantasmas. A confirmação de fundo limpo é uma declaração editorial: o código não consegue comprovar isso visualmente.

Para um efeito sonoro: sound_effects é uma lista de objetos com file, offset_seconds, duration_seconds, volume e rights. Para a trilha: music tem file, volume e rights. Só são aceitas origens documentadas (creator_original, public_domain_verified, properly_licensed).

Os nomes dos arquivos são restritos a uma única pasta do episódio, sem caminhos absolutos ou atravessar diretórios.

## Comandos de uso futuro (NÃO executar durante a manutenção)

Para somente montar as props offline, depois de obter artes, poses e narração com direitos verificados:

    python scripts/otaku_multicena_quality_v3.py --manifest "caminho/quality.json" --captions "caminho/marcacoes-remotion.json" --public-root "motion-remotion/public" --output "caminho/props-v3.json"

Para auditar um vídeo de prévia já existente, sem realizar upload:

    python scripts/otaku_multicena_video_qa.py --video "caminho/preview.mp4" --output "caminho/qa-video.json"

Nenhum dos comandos cria um vídeo nem publica no YouTube. O QA retorna sempre status NEEDS_MANUAL_REVIEW_BEFORE_PUBLICATION, mesmo quando os requisitos técnicos passam.

## Pendências reais antes de voltar à geração

1. O gerador atual ainda produz cinco imagens. Aumentar para 8–12 planos com custo e consistência controlados exige nova implementação e aprovação de orçamento; não burlar esse limite durante a pausa.
2. É necessário criar poses realmente diferentes, fundos limpos e revisar identidade, enquadramentos e coerência de ação visual — os testes atuais têm apenas imagens sintéticas.
3. Falta testar um MP4 real do novo perfil, verificar sincronismo, pronúncia, SFX, direitos, legendas e transições. Validadores técnicos não substituem inspeção humana.
4. Ainda falta integrar o perfil opcional V3 ao orquestrador para novos Shorts; não trocar retrospectivamente mídia de episódios publicados.
5. Publicação só pode ser retomada com novo consentimento explícito do criador, depois da manutenção concluída. Os Shorts pendentes 5 a 1 permanecem bloqueados.

Os dados da auditoria são hipóteses para roteiros, não garantia de visualizações. Qualidade do vídeo é prioritária sobre volume de uploads.
