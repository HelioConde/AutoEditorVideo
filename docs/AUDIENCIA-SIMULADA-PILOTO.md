# Piloto — Laboratorio de Audiencia do AutoEditorVideo

## Objetivo
Auditoria editorial **antes de gerar imagens** para tres roteiros do Otaku Multicena BR.
Inspirado no uso de diferentes perfis para analisar decisoes, mas **nao incorpora
o codigo do MiroFish**. Nenhuma dependencia externa, API, memoria persistente,
proxy ou conta extra e necessaria na fase 1.

## O que faz
- Le somente o manifesto existente de 15 videos e seleciona os tres IDs BR:
  5015 (Jujutsu Kaisen), 5016 (Dungeon Meshi), 5017 (Attack on Titan).
- Aplica seis rubricas explicitas: gancho, clareza, ritmo, estrutura,
  desfecho e metadados.
- Agrega cinco perspectivas editoriais deterministicas com pesos diferentes:
  iniciante, fa de anime, espectador de celular, revisor critico e recorrente.
- Verifica se o gancho cadastrado aparece no inicio da narracao real.
- Devolve observacoes acionaveis e tres aberturas para *revisao humana*
  (primeira frase narrada, gancho cadastrado e frase de conclusao).
- Exporta JSON com hashes SHA-256 das narracoes para permitir comparacoes
  entre versoes sem reescrever o roteiro ou mexer na producao.

## Limites importantes
**Nao e simulacao de seres humanos nem de audiencia real.** Os cinco
"agentes" sao apenas criterios de revisao independentes, nao LLMs
autonomos. O indice 0–100 e uma pontuacao heuristica e nao corresponde
a chance de viralizar, ao percentual de retencao ou a views previstas.
A pontuacao nao habilita, impede, agenda ou modifica upload.

Nao acessa APIs de YouTube ou vidIQ, dados privados de publico, imagens,
reconhecimento facial, OAuth, secret nem modelos pagos. Tambem nao substitui
validacao de fatos, direitos autorais, conteudo infantil e qualidade visual.

## Como testar
No repositorio, com Python 3.11 ou superior:

    python -m unittest discover -s tests -p test_audiencia_simulada.py -v

    python scripts/audiencia_simulada.py \
      --manifest conteudos/lote-15-canais-20261108.json \
      --ids 5015-jujutsu-kaisen-dominio 5016-dungeon-meshi-masmorra 5017-attack-on-titan-muralhas \
      --channel br --output reports/audiencia-simulada-br-piloto.json

No PowerShell o comando acima pode ser fornecido em uma linha unica.

O GitHub Actions "Laboratorio de Audiencia (piloto seguro)" roda os testes e
gera o artefato audience-lab-br-pilot quando ha Pull Request. Nao publica videos.

## Proximos passos, somente depois de revisar este piloto
1. Validar as sugestoes em 3 roteiros BR; corrigir falsas advertencias.
2. Quando houver dados oficiais de desempenho disponiveis, relacionar
   videos publicados e seus IDs/metricas reais por canal e data.
3. Medir se o laboratorio melhora o processo de edicao, com comparacao
   entre roteiros revisados e grupo de controle — sem afirmar causalidade.
4. Opcionalmente testar agentes LLM em execucao limitada, com orcamento
   explicito e autorizacao, sem acoplar o sistema MiroFish completo.
5. Manter o fluxo atual de uploads independente enquanto o piloto e validado.

## Melhorias do segundo ciclo
- **Gancho literal x reformulado:** a sobreposicao de palavras relevantes distingue
  `literal`, `vocabulario_relacionado` e `revisar_abertura`.
  A ferramenta nao determina equivalencia semantica nem intencao.
- **Desfecho:** a expressao 'No fundo' conta como marcador possivel de
  conclusao, reduzindo falsos alarmes no roteiro Dungeon Meshi.
- **Sincronia:** compara a narracao completa com a concatenacao das cenas;
  divergencia gera alerta antes da producao dos assets.
- **Relatorio legivel:** use `--markdown-output reports/audiencia-simulada-br-piloto.md`
  para gerar uma versao humana juntamente com o JSON.
- **CI:** exporta JSON e Markdown em cada PR; depois de merge na branch
  principal, tambem executara uma verificacao diaria por GitHub Actions.
  Agendamentos no GitHub so executam a versao do workflow no branch default.
  Um monitoramento separado no ChatGPT foi ativado para acompanhar o piloto.

**Nota:** vocabulario relacionado nao equivale a promessa narrativa cumprida.
A avaliacao sempre exige revisao editorial; nao altera videos nem uploads.
