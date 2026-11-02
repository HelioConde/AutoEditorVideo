# Arquivo Otaku: plano editorial v0.9

Novo núcleo offline integrado gradualmente ao repositório.

- Escolha um episódio JSON com roteiro e cenas próprios; nenhum nome de anime é fixo no código.
- Planeje cortes seguindo tempos de legendas SRT, ou gere uma estimativa identificada como tal.
- Identifique imagens escuras e resolução baixa usando Pillow.
- Identifique planos longos e roteiros sem revisão factual.
- Este comando não chama IA nem publica vídeos; o publicador OAuth permanece independente.

Comando Windows: python -m arquivo_otaku.pipeline --episodio arquivo_otaku/episodios/death-note.json --srt caminho/legendas.srt

Testes: python -m unittest discover -s arquivo_otaku/tests -v

Atenção: o pacote local Arquivo Otaku v0.8 (gerador, editor, miniaturas e YouTube OAuth) ainda precisa ser sincronizado integralmente neste repositório. O editor antigo continua disponível e está salvo na branch backup/autoeditor-studio-2026-11-01. Não remova credenciais locais.
