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
A publicação de um Short com 100% das cenas apenas em arte plana é bloqueada
até que exista ao menos uma cena com personagem em camada segura; o produtor
não inventa movimento que não existe.

## Etapa 1 — validar e preparar sem gastar IA

```powershell
cd "$HOME\Documents\arquivo-otaku-github"
git pull --ff-only origin main

.\grade-50-shorts.ps1 -Acao Validar -Quantidade 50
.\grade-50-shorts.ps1 -Acao Preparar -Quantidade 50
```

Essas ações geram/validam storyboards e metadados locais. **Nenhum upload**.
Também podem ser usadas com `-InicioNaLista 1 -Quantidade 3`.

## Etapa 2 — testar o primeiro vídeo, sem publicar

```powershell
Push-Location .\motion-remotion
npm.cmd run typecheck
npm.cmd run test:qa
Pop-Location
.\.venv\Scripts\python.exe -m pytest -q tests/test_grade_50_shorts.py

# Até 30 chamadas adicionais para este episódio. É um teto, não uma previsão
# de custo ou garantia de render concluído; requer proxy elegível.
.\grade-50-shorts.ps1 -Acao Produzir -InicioNaLista 1 -Quantidade 1 `
  -Modelo gpt-image-2 -Perfil equilibrado `
  -MaxChamadasPorVideo 30 -ConfirmarCotaImagem
```

Use `-MaxChamadasPorVideo 0` para trabalhar só com cache. Se o episódio
precisar de mais imagens, o editor interromperá **antes de começar** a geração
daquele episódio; ajuste o teto conscientemente. Não use 50×30 sem considerar
o custo/limite: o máximo teórico é **1.500 chamadas**.

Antes de publicar, **assista ao MP4** em tamanho de celular e confira:
1. Abertura sem pulos de posição; zoom suave perceptível.
2. Camadas do personagem realmente se movimentam quando seguras; sem
   braços/rosto esticados e sem arte tremendo.
3. Legendas no tempo certo, legíveis e fora do rosto.
4. Identidade do personagem, cenário e objeto corretos.
5. Duração real até 60,000s aferida por ffprobe.
6. Correção editorial e direitos de uso de toda arte/áudio.

Para produzir outros episódios, ajuste `-InicioNaLista` e `-Quantidade`.
O lote para após a primeira falha; o cache e o estado anterior são preservados.

## Etapa 3 — agendar **somente vídeos prontos** no YouTube

O agendamento exige aprovação **explícita** e data futura com fuso.
Publicações são enviadas como **private** com `publishAt` confirmado pela API
do YouTube; tornam-se públicas na data marcada, não imediatamente.
Por exemplo, depois de produzir e conferir toda a grade:

```powershell
.\grade-50-shorts.ps1 -Acao Agendar -InicioNaLista 1 -Quantidade 50 `
  -InicioAgendamento "2026-12-01T09:00:00-03:00" `
  -IntervaloHoras 24 -ConfirmarPublicacao
```

**Altere a data para uma futura quando for executar.**
A fila usa a posição original 1–50 para calcular as datas; cada vídeo
fica separado por 24 horas na programação. Com `-Quantidade 3`, você
pode validar os primeiros três sem enviar os demais.

Proteções: antes de qualquer upload, verifica os MP4s, capas, duração e
metadados de animação; não aceita 50 vídeos sem personagem realmente
separado em camada; usa `-MaxChamadas 0` na publicação; não reenvia
conteúdo que já tem estado confirmado, nem tenta repetir um upload remoto
que falhou de modo ambíguo. Guarde o estado
`assets/gerados/publicacao-youtube/grade-50-estado.json` no PC.

## Estratégia recomendada

A lista contém animes recentes, populares e nostálgicos. Não foi
projetada como 50 publicações ao mesmo instante: faça testes de desempenho
das primeiras 3–10 publicações e compare retenção inicial, visualizações
intencionais e inscritos antes de usar todo o orçamento.

**Não é possível transformar uma imagem chapada em animação facial real
apenas com zoom**. Quando isso for essencial, prepare outras camadas
aprovadas ou um fluxo de animação independente, preservando a identidade
da ilustração e as restrições de direitos/licença.
