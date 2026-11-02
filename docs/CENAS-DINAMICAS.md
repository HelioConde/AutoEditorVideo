# Planejamento de cenas adaptativo — roteiro é a fonte

A quantidade de cenas **não** é 5, 7 nem 9 por padrão. Uma história curta
com um único acontecimento pode ter **1** cena; uma história com vários
acontecimentos, revelações e mudanças de foco terá quantas cenas fizerem
sentido. O limite técnico de 60 apenas impede lotes acidentais gigantes.

## Critério editorial

1. Uma cena corresponde a um **acontecimento visual ou mudança relevante de foco**.
2. Uma fala longa sobre a mesma ação pode manter o mesmo cenário e variar
   zoom/câmera, sem obrigar outra imagem nem gastar outra chamada.
3. Uma revelação, ação nova, novo personagem ou local sugere uma nova imagem.
4. Um objeto pode ter camada animada independente; isso não cria outra cena.
5. Se houver dúvida, o editor pode definir cortes manualmente. A heurística
   local não substitui uma direção visual humana ou da IA.

## Planejar sem gastar cota

Na raiz do repositório no PowerShell:

```powershell
.\planejar-cenas.ps1 -Id 003-death-note-xadrez
```

A saída vai para
`assets/gerados/planos-visuais/003-death-note-xadrez-cenas.json`.
Ela inclui trecho narrado, motivo da troca, durações **estimadas**,
e campo vazio para escrever um prompt visual para cada acontecimento.
Nenhum vídeo é gerado ou enviado ao YouTube.

Para controlar por roteiro explícito, acrescente `blocos_visuais` no JSON
do episódio. A concatenação dos blocos precisa reproduzir exatamente o
roteiro, mantendo todas as falas na ordem correta.

```json
{
  "id": "exemplo",
  "script": "Light observa o tabuleiro. Mas L percebe a armadilha.",
  "blocos_visuais": [
    "Light observa o tabuleiro.",
    "Mas L percebe a armadilha."
  ]
}
```

Outra opção é separar parágrafos ou usar `[[CENA]]` entre trechos.
A primeira execução é uma **proposta editorial**: revise os pontos de corte e
preencha os prompts antes de autorizar chamadas ao gerador.

## Sincronização

O planejador estima segundos pela quantidade de palavras. Isso **não** é
sincronização exata; para renderizar deve-se usar os tempos efetivos do TTS
ou das legendas. A quantidade de cortes deve respeitar o roteiro, não
uma meta de 3 segundos por imagem.

## Compatibilidade

Esta atualização altera o planejador offline e elimina limites artificiais
nas validações existentes. O renderizador Remotion de uma só composição e
o pacote de imagens-mãe v1.3 distribuído anteriormente ainda precisam
receber integração direta com o JSON adaptativo para montar automaticamente
um vídeo inteiro. Não confunda gerar um plano com gerar o Short final.
