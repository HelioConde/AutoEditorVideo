# Grade de 50 Shorts — Otaku Multicena

**Status:** 50 roteiros + títulos + ganchos + capas + descrições registrados no
GitHub. **Nenhum dos 50 Shorts foi gerado ou publicado por este cadastro.**
A geração de PNG/voz/MP4 e o upload OAuth só rodam no computador Windows do
criador, com cache e credenciais locais. O editor não promete execução em segundo
plano na nuvem.

## Conteúdos

- `conteudos/otaku-multicena-grade-50-a.json`: #1–25, começando por Black Clover.
- `conteudos/otaku-multicena-grade-50-b.json`: #26–50, terminando em Fullmetal Alchemist: Brotherhood.
- IDs `5001-black-clover` ... `5050-fullmetal-alchemist-brotherhood`.
- Conteúdo é **comentário original e introdutório**, não reprodução de episódios
  ou falas dos personagens. Metadados usam #OtakuMulticena; a voz não fala
  o nome da marca. Verificar a fidelidade de cenas, nomes e fatos antes de publicar.
- Sem baixar trechos, músicas ou quadros protegidos sem autorização.
  Ilustrações geradas por IA não garantem direitos de uso de franquias.

## Correção obrigatória do efeito de "fliques"

O motor anterior introduzia jump cuts artificiais de posição no mesmo PNG em
1,25s, 2,45s e a cada 2,7s. O usuário relatou desconforto.

**Novo padrão:** entrada suave com zoom in/out centralizado (amplitude extra
até 4% na abertura) + respiração de zoom de até 2,2% em planos muito longos.
O pan é quase zero e não há saltos internos de enquadramento.

Nas camadas semânticas RGBA seguras, os personagens têm movimento rígido
suave porém mais perceptível no preset equilibrado: sem distorcer rostos,
dedos e roupas. Em artes planas, só há animação de câmera, **não há
animação real de braços, boca ou rosto**. O relatório
`qa-master-multicenas.json` registra `camera_only_scenes`.
O fluxo padrão produz sobretudo **2.5D/imagem plana**. Essas cenas
podem ser publicadas normalmente após os demais testes de QA, usando
**zoom in/out suave**. O QA avisa que não existe movimento independente
de personagens, sem fingir gestos que a arte não possui.

Quem quiser um modo mais rigoroso pode adicionar
`-ExigirMovimentoPersonagem`: somente nesse caso o lote bloqueia
vídeos sem nenhuma camada de personagem RGBA segura. O padrão NÃO usa
esse bloqueio, pois ele impedia a publicação de vídeos válidos como o
`5001-black-clover`.

## Etapa 1 — validar e preparar sem gastar IA

```powershell
cd "$HOME\Documents\arquivo-otaku-github"
git pull --ff-only origin main

.\grade-50-shorts.ps1 -Acao Validar -Quantidade 50
.\grade-50-shorts.ps1 -Acao Preparar -Quantidade 50
```

Essas ações geram/validam storyboards e metadados locais. **Nenhum upload**.
Também podem ser usadas com `-InicioNaLista 1 -Quantidade 3`.

## Etapa 2 — gerar E PUBLICAR como público, vídeo por vídeo

A preferência atual do criador é **sem agendamento**. Assim que o Short
estiver renderizado, com duração/capa/QA aprovados, o lote fará o upload
**público**, verificará o ID e tentará enviar a miniatura 9:16.
Só depois começa o próximo anime. Não haverá pausa de aprovação manual
entre os vídeos, portanto faça primeiro um teste pequeno se quiser
comparar a aparência das animações.

```powershell
Push-Location .\motion-remotion
npm.cmd run typecheck
npm.cmd run test:qa
Pop-Location
.\.venv\Scripts\python.exe -m pytest -q tests/test_grade_50_shorts.py

# Primeiro Short: produz e publica como PUBLICO automaticamente.
.\grade-50-shorts.ps1 -Acao ProduzirPublicar -InicioNaLista 1 -Quantidade 1 `
  -Modelo gpt-image-2 -Perfil equilibrado `
  -MaxChamadasPorVideo 30 -ConfirmarCotaImagem -ConfirmarPublicacao
```

Para processar **todos os 50** em sequência, altere `-Quantidade 1`
para `-Quantidade 50`. `30` é o teto **por vídeo**; 50×30 permite
até **1.500 chamadas de imagem**, não é uma previsão de gasto nem
garantia de conclusão. Cenas podem exigir mais de 30 chamadas. Sem
`-ConfirmarCotaImagem`, nenhuma chamada de geração é liberada quando
o teto é maior que zero. Com `-MaxChamadasPorVideo 0`, a etapa de
produção usa somente imagens já em cache.

Para **somente produzir, sem publicar**, use `-Acao Produzir`.
`-Acao Validar` e `-Acao Preparar` continuam disponíveis e não
usam créditos de imagem nem enviam vídeos.

## Proteções e envio da miniatura

- Não publica vídeos incompletos: exige MP4 válido de até 60 segundos,
  JPEG 9:16, QA recente e relatório correspondente ao arquivo de vídeo.
  Cenas 2.5D/planas com zoom suave **são permitidas**; não são
  consideradas animação independente de personagem. Use
  `-ExigirMovimentoPersonagem` se quiser bloquear essas produções.
- Publica **um vídeo por vez**, como `public` — nunca `private` ou
  `publishAt`. Se o YouTube não confirmar a visibilidade pública,
  a fila para e registra a incerteza; verifique o Studio.
- O publicador espera a API do YouTube confirmar
  `processingDetails.processingStatus=succeeded` antes de chamar
  `thumbnails.set` para a **capa vertical gerada pelo editor**.
  A disponibilidade depende de verificação/permissões da conta.
  Se houver 403, processamento pendente ou recurso indisponível,
  a capa continua salva em `assets/gerados/publicacao-youtube`,
  o vídeo continua publicado e **não é reenviado**.
  Miniaturas personalizadas de Shorts também podem ser ajustadas
  no YouTube Studio para desktop, em canais elegíveis.
- Os registros de vídeo e SHA de MP4 são preservados em
  `assets/gerados/publicacao-youtube/grade-50-estado.json`.
  Em falhas ambíguas de upload, interrompe e pede verificação no
  YouTube Studio em vez de arriscar duplicação.
- O software só consegue executar enquanto o processo PowerShell
  estiver rodando no PC. Os arquivos no GitHub não iniciam tarefas
  automaticamente.

## Estratégia recomendada

A lista contém animes recentes, populares e nostálgicos. Embora o modo automático já permita 50 uploads públicos sequenciais,
vale medir os primeiros resultados e a qualidade visual para evitar
repetir problemas nos próximos vídeos.

**Não é possível transformar uma imagem chapada em animação facial real
apenas com zoom**. Quando isso for essencial, prepare outras camadas
aprovadas ou um fluxo de animação independente, preservando a identidade
da ilustração e as restrições de direitos/licença.
