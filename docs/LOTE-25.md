# Arquivo Otaku — Lote de 25 vídeos (primeira etapa)

A geração de **25 roteiros completos, 25 vídeos e 25 uploads públicos** não está implementada nesta versão.
Esta entrega cria uma **fila editorial de 25 assuntos** e um executor de renderização
local que só processa episódios com JSON revisado e aprovado, sem upload automático.

## Por que existe a revisão

A política oficial do YouTube proíbe inundar a plataforma com conteúdo
automatizado substancialmente repetitivo. A monetização de conteúdo em massa
também pode ser recusada.

Fontes:
- https://support.google.com/youtube/answer/2801973?hl=pt-br
- https://support.google.com/youtube/answer/1311392
- https://support.google.com/youtube/answer/57407?hl=pt-BR

25 pautas são experimentos **editoriais**, não 25 roteiros prontos. Para
cada pauta, criar `conteudos/<id>-direcao.json`, com 5–20 cenas, roteiro
autoral, prova da obra e gancho. Apontar esse arquivo no campo `episodio`
do manifesto. Marcar `aprovado`, `checagem_factual`, `direitos_revisados`
como `true` **apenas depois** de realmente revisar cada requisito.

## Comandos

```powershell
# Inspecionar a fila sem IA nem upload
.\lote-25.ps1 -Acao status

# Simular a renderizacao, sem IA nem upload
.\lote-25.ps1 -Acao renderizar

# Apenas para roteiros efetivamente aprovados e com assets:
.\lote-25.ps1 -Acao renderizar -ConfirmarRender

# Prototipos offline, sujeito a erro se as imagens antigas nao correspondem:
.\lote-25.ps1 -Acao renderizar -ConfirmarRender -ReutilizarImagens
```

O estado de cada MP4 fica em `assets/gerados/lotes/lote-25-resultados.json`.
Os vídeos prontos passam por inspeção FFprobe (formato, resolução, áudio e duração).
No caso de falha, o lote pode ser retomado sem regenerar MPs aprovados
que ainda correspondam ao mesmo JSON.

**Importante:** o executor não usa o novo motor 2.5D de camadas e não
publica nada. Ele invoca o renderizador atual MoneyPrinterTurbo, que ainda
precisa de integração com o motor de camadas PNG para animação real.

## Próximas dependências técnicas

1. Gerador de roteiro original por pauta, com fontes verificadas.
2. Geração de personagem PNG com alpha ou remoção de fundo; cenários e objetos separados.
3. Compositor 2.5D por cena e narração sincronizada; integrar ao MPT.
4. QA audiovisual e editorial, incluindo repetição e direitos autorais.
5. Agendamento de publicação aprovado, respeitando limites reais do canal
   e armazenando o ID de cada upload para evitar duplicidade.

**Não existe garantia de que seu canal permita 25 uploads num dia.**
O limite diário da conta e as restrições da API precisam ser verificados no
YouTube Studio e no Google Cloud.
