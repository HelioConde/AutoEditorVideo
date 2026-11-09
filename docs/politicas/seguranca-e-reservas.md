## INTEGRACAO OAUTH DOS TRES NOVOS CANAIS — GITHUB CLOUD-FIRST

- Uma identidade registrada NÃO autoriza upload. Gamer/Kids/Alchemy
  exigem consentimento Google e refresh token próprios. Os CINCO canais
  compartilham APENAS o Environment GitHub youtube-private-upload,
  restrito EXCLUSIVAMENTE à branch main. São 5 Secrets OAuth diferentes
  (BR, EN, GAMES, KIDS, ALCHEMY) e 1 YOUTUBE_CLIENT_JSON existente.
  Isso reduz o isolamento entre jobs: nunca expor todos os Secrets a um
  processo, registrar credenciais, aceitar canal sem checagem de ID ou
  habilitar uploads automaticamente.
- A verificação de cada Environment acontece sem Secrets no workflow
  .github/workflows/youtube-new-channels-oauth.yml. A autenticação cloud
  é SOMENTE channels.list(mine=true), sem videos.insert ou upload.
- A primeira autorização OAuth ocorre no navegador do proprietário via
  conectar-novos-canais.ps1 / scripts/youtube_new_channels_oauth.py,
  com comparação EXATA do YouTube Channel ID. É proibido enviar tokens
  à conversa, commits, logs públicos ou artifacts.
- Só transferir OAuth ao GitHub após consentimento explícito do titular
  para guardar refresh tokens no Environment existente e protegido.
- Após OAuth validado, construir fluxos cloud de geração, QA, miniatura
  original e publicação privada por canal; não habilitar upload ao
  cadastrar/verificar OAuth. Gamer exige visuais IA ilustrativos, nunca gameplay real; Kids requer
  privacidade de referências e direitos das músicas; Alchemy requer
  demonstrações técnicas verificáveis.
- Guia operacional: docs/CONECTAR-3-CANAIS-OAUTH-GITHUB.md.

## REGRA — CINCO CANAIS YOUTUBE SEPARADOS (05/11/2026)

- Registro oficial: config/youtube-channel-registry.json; validar com scripts/youtube_channel_registry.py. Sao **cinco canais**, sem reutilizar ID, OAuth, thumbnail, voz ou metadados de outro.
- Otaku Multicena BR: UCXGYTuBYn-0Ziqin5ajKhOw; Otaku Reframe EN: UCBoNbQjaMYdpJqPLRZAFkvQ (uploaders existentes preservados).
- Gamer: UCg77gYc1_wkHuL07XPtKcow; YouTube exibe **Hélio Conde**, **Conde Games** e proposta ainda nao aplicada na conta. Exigir ilustrações originais geradas por IA, sem simular gameplay.
- Kids: UCxEzVW2Uy44OUVurTQSg_Eg; YouTube exibe **Emanuelly Kids**, a serie oficial e **Fofinhos**. Toda publicacao para criancas deve ter classificacao Made for Kids, sem CTA para comentarios/inscricoes de criancas. Nunca publicar fotos privadas nem musicas sem direitos.
- Alchemy Lab: UCCTYFE5Cmz2aYZ37cJQ-wcg; YouTube exibe **Alchemy Flames**; a identidade planejada e **Alchemy Lab** (IA pratica e automacoes). Nunca afirmar que o nome foi alterado na conta; nunca falsificar testes ou criar conteudo repetitivo de baixo valor.
- Os tres novos canais estao **somente registrados**, com publicacao cloud DESATIVADA; os tokens individuais sao adicionados com consentimento ao Environment existente youtube-private-upload, preservando YOUTUBE_CLIENT_JSON e os tokens BR/EN. Nao criar Environments adicionais. Cada verificacao consulta channels.list(mine=true) e bloqueia qualquer ID incorreto. Nunca usar segredos Otaku/CodeX Proxy como substitutos.
- Manter roteiros/miniaturas originais, categoria e idioma por canal, default privado, verificacao de direitos, QA e controle de duplicatas. Os pilotos antigos Checkpoint Pixel/MiniMundo Curioso permanecem isolados com upload_enabled=false e IDs nulos; sao drafts, NAO sao identidade do Emanuelly Kids.
- Reservar cada (canal, episodio) antes de gerar scripts, comandos PowerShell ou MP4s usando conteudos/otaku-production-reservations.json, agora compatível com cinco canais; nenhum upload e geracao sao autorizados apenas pelo registro.
- Guia: docs/CANAIS-5-YOUTUBE-GITHUB.md.


## REGRA PERMANENTE — RESERVAR NO GITHUB ANTES DE QUALQUER VIDEO/COMANDO

**Regra definida pelo criador em 05/11/2026:** toda vez que solicitar ao
ChatGPT/Codex um script, comando PowerShell, workflow, lote ou vídeo para gerar,
**registrar primeiro no GitHub** o episódio e o canal como `reserved` ou
`in_production` em `conteudos/otaku-production-reservations.json`.
O registro deve ser integrado à `main` antes de consumir chamadas de imagem.

- A reserva é por par `channel + id`: BR Otaku Multicena e EN Otaku
  Reframe têm estados e OAuth independentes.
- A geração cloud deve exigir a reserva correta com
  `scripts/production_reservations.py` e seu `reservation_owner`.
  Ausência de registro, reserva de outro job, `published`,
  `in_production`, `existing_assets_unverified` ou vídeo já gerado
  bloqueiam a seleção automática. Nunca assumir que falta de pasta significa
  vídeo inédito ou que uma pasta prova publicação.
- A fila atual: `5009-overgeared` e `5010-aoashi` em produção pelo
  criador (não usar de novo); `5008-firefly-wedding` já publicado;
  `5011-gachiakuta` reservado para **dois Shorts separados BR e EN**;
  depois disso, o próximo candidato BR é `5012-solo-leveling`, sujeito
  a nova verificação no canal e à reserva antes de qualquer script.
- Antes de escolher novo episódio, conferir o registro versionado e, quando
  disponível, o histórico do YouTube incluindo privado/agendado; registrar
  alterações observadas. Se houver conflito, bloquear em vez de gerar outro vídeo.
- Publicar privado por padrão, **apenas** com token OAuth do canal identificado
  e verificado. Não inferir autorização do YouTube a partir de sessão OAuth do
  proxy de imagens. Agendar somente se data e hora forem definidas.
- A regra vale também se o usuário pedir só um comando ou PowerShell para gerar
  vídeo, não apenas quando solicitar uma produção completa. O registro precisa
  preceder a entrega do comando; não depender de memória de conversa.

- Nunca enviar `.env`, `.secrets`, tokens OAuth, credenciais de terceiros, vídeos,
  imagens geradas, caches nem dados de conta ao repositório.
- Toda geração de imagens deve considerar cotas e respeitar `no available accounts`.
  Não contornar cotas, não trocar conta automaticamente para burlar limites.
- `-SomenteConfigurar`, QA, radar e testes não podem gastar cota nem publicar.
- Evitar upload duplicado; publicar apenas quando o usuário solicita. Confirmar
  o modo de privacidade e registrar o ID retornado.
- Não inventar métricas, fontes de notícias nem prometer monetização.
- Interface do GitHub Pages é informativa, não executa o backend Windows.
- Usar `python -m pytest -q tests` antes de entregar mudanças funcionais.
- Para conteúdos de anime, revisar direitos de imagem, música e fontes originais.
