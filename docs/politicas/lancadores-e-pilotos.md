## POWERHELL DEDICADO — GAMES PT-BR / OTAKU REFRAME EN

- `canal-gamer.ps1` encaminha EXCLUSIVAMENTE `-Canal games` ao motor
  `piloto-canais-v3.ps1`. Recusar IDs Kids, forcar IDs individuais para
  `Voz` e `Renderizar`, nunca publicar ou usar OAuth.
- `canal-ingles.ps1` encaminha `PublicadosBR` ao preparador EN V3
  e ao renderizador EN; aceita `Legado` isoladamente. Voz `en-US-GuyNeural`
  e canal-alvo Otaku Reframe `UCBoNbQjaMYdpJqPLRZAFkvQ`.
- EN `Enviar` exige `-Id`, `-ConfirmarEnvio`, canal ID local identico,
  e `-ConfirmarPublico` adicional para privacidade `public`. Privacidade
  default `private`. Nunca enviar lotes acidentalmente.
- O canal Kids usa o `piloto-canais-v3.ps1 -Canal kids` existente.
- Teste `tests/test_channel_launchers.ps1` em Windows com motores fake,
  sem acessar YouTube, TTS ou imagens. Leia
  `docs/POWERSHELL-CANAIS-GAMER-INGLES.md`.
- Nenhuma mudanca nos scripts do canal anime BR sem pedido explicito.

## GAMES + KIDS — PILOTO 3x2 PT-BR

- Os dois novos canais sao totalmente PT-BR; NAO usar Otaku Reframe/ingles.
- Games (nome provisório Checkpoint Pixel): 3 Shorts com Minecraft, Roblox
  e TILLFOLK; requires first-party or licensed gameplay from local captures;
  jamais simular jogadas, vitória ou mecânicas não implementadas.
- Kids (nome provisório MiniMundo Curioso): 3 Shorts educativos originais
  sobre cores, contagem 1-5 e formas, para crianças de aproximadamente 4-7.
  Conteúdo dirigido a crianças: marcar Made for Kids true; nao pedir comentarios,
  inscricoes, compras ou engajamento; materiais suaves e apropriados à idade.
- As vozes são pt-BR-AntonioNeural para Games e pt-BR-FranciscaNeural para Kids.
- Conteudos/piloto-games-kids-3x2-v3.json é a fonte dos seis storyboards e
  metadados. O Remotion possui composicao original PilotoCanaisV3, com SVG Kids
  e videos capturados reais para Games. Nao inventar assets faltantes.
- Nomes e IDs dos canais ainda nao existem no projeto: youtube_channel_id=null.
  Nunca utilizar tokens, channel IDs ou uploads Otaku para novos canais.
- O piloto-canais-v3.ps1 so prepara/inspeciona/gera voz/renderiza localmente,
  sem autenticar/publicar. Cada render depende de TTS PT-BR e QA tecnico.
  Publicar só após criação, verificação OAuth independente e autorização explícita.
- Contar resultados por 1/6/24/72/168 horas e não presumir 3 impulsos diários.
- Docs: docs/PILOTO-GAMES-KIDS-3X2-V3.md.
