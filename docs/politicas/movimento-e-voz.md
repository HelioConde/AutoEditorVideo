## PADRAO VISUAL ATUAL: ZOOM CONTINUO SEM FLIQUES (2026-11-03)

- O criador rejeitou os **jump cuts virtuais** em 1,25s / 2,45s e as
  trocas de posicao a cada 2,7s; causavam desconforto e atrapalhavam
  a percepcao do movimento do personagem. **Nunca reintroduzir**.
- Abertura: zoom in / zoom out suave de ate 4% com curva continua;
  long holds: respiracao de camera de ate 2,2% sem saltos. Pan global
  quase zero; camera centrada em cada cena. Nunca alterar o ponto focal
  abruptamente em uma mesma imagem.
- Personagens com RGBA semantico seguro: movimento rigido de corpo inteiro,
  sem alongar rostos, maos, pernas ou tecidos. Preset equilibrado permite
  deslocamento mais perceptivel, mas bloqueia personagens encostados em
  objeto/manga/maos com risco de descolamento.
- **Arte plana nao pode ter membros articulados de verdade** apenas com
  transformacao global. Informar `camera_only_scenes` no QA; se o
  movimento de corpo for indispensavel, produzir camadas/frames realmente
  aprovados em vez de prometer gestos inexistentes.
- Texto/legendas: blocos de ate 3 palavras, fundo escuro, tempos reais
  da voz Edge TTS/ASR. Nao pronunciar o nome do canal no CTA.
- Evitar reenquadramento excessivo, flicker, jitter, transicoes rapidas
  e fontes cobrindo o rosto. Validar quadros e o video final no celular.
- Alteracoes no motor de render invalidam MP4 local (renderer_sha256).
  Nao reenviar videos antigos automaticamente.

## REGRA EDITORIAL: CTA SEM MARCA NA NARRACAO

- Em novos roteiros PT-BR, manter um CTA curto e natural, como
  `Inscreva-se para acompanhar o proximo episodio!`.
- **Nao narrar o nome "Otaku Multicena"** no CTA final. A marca continua
  no titulo, descricao, hashtags, capa e elementos visuais quando apropriado.
- Aplicar em roteiros novos ou em edicoes explicitamente solicitadas; nao
  reescrever audios de Shorts ja publicados sem pedido.
- Quando editar o campo `script`, atualizar o campo `cta` correspondente e
  invalidar voz/legendas/MP4 em cache se as palavras faladas mudarem.
- Edge TTS segue o motor padrao. Nenhum upload automatico decorrente de revisao
  textual; exigir o sinalizador de publicacao explicito.

## MOTOR DE VOZ OPCIONAL: VOICESTUDIO

- Edge TTS e a opcao **padrao** e nunca deve ser removida nem substituida silenciosamente.
- `-VozMotor voicestudio` seleciona o VoiceStudio apenas explicitamente no pipeline PT-BR.
- Primeiro teste: `testar-voz-studio.ps1`; nenhuma imagem, render ou upload.
- No VoiceStudio, legendar **somente** com tempos reais de ASR; falha de servidor,
  modelo, transcricao ou tempos bloqueia a geracao. Nao fabricar word boundaries,
  nao misturar cache de Edge e VoiceStudio e nao reutilizar MP4 com voz incorreta.
- Restrito a API local 127.0.0.1 / localhost, sem credenciais publicadas no repo.
- Licencas dos modelos de voz precisam ser verificadas antes de uso monetizado;
  pesos OmniVoice padrao podem ter restricao NC. Conservar audio em cache local.
