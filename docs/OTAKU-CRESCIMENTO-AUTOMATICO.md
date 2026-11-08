# Otaku Multicena — melhoria automática baseada em métricas

**Ativo desde 08/11/2026.** O objetivo é usar resultados medidos
para melhorar FUTURAS decisões de roteiro, direção, títulos, narração,
legendas, miniaturas, duração e tipos de conteúdo. Não altera vídeos antigos.

## Circuito de aprendizagem

1. A tarefa Monitorar Otaku Multicena consulta YouTube/vidIQ quando
   credenciais, disponibilidade e cotas permitirem. Não inventa métricas.
2. Cada observação verificável é salva em dados/metricas-redes/,
   distinguindo métricas vitalícias, semanais e de 28 dias.
3. O workflow **Otaku Multicena - Autotune editorial baseado em dados**
   roda após atualização desses snapshots e diariamente (20:00 UTC).
4. O script scripts/otaku_growth_autotune.py lê o snapshot mais recente
   com schema reconhecido, canal validado e data não futura. Calcula
   regras conservadoras em config/otaku-growth-active-v1.json.
5. O GitHub Actions só registra a configuração se os dados forem coerentes
   e os testes de regressão passarem. Sem chamadas de imagem, tokens ou MP4.
6. scripts/otaku_growth_v3.py aplica avisos sobre hooks, títulos,
   final de vídeo, narração da marca e texto da capa. 
   scripts/roteiro_para_storyboard.py orienta a primeira cena para
   uma ação presente no roteiro, sem fingir animação.
   scripts/planejador_editorial.py integra as regras de narração,
   legendas, miniaturas e duração ao planejamento.
   scripts/otaku_multicena_strategy_plan.py recebe as variantes
   de conteúdo para experimentação.

## Evidência disponível em 08/11/2026

- YouTube Studio, últimos 28 dias (captura): **34,8% continuaram
  assistindo e 65,2% ignoraram**. É uma métrica de decisão no feed,
  NÃO o percentual de retenção ou conclusão do vídeo.
- YouTube Analytics API via vidIQ, 09/10–07/11: **7.535 views** e
  **2.728 engaged views** no BR, em outra janela.
- Recap semanal, 26/10–01/11: **dois Shorts**, **58 curtidas** e
  **três inscritos ganhos**. Não somar diretamente com janela de 28 dias.
- Referências criativas: Light/Kira, Steel Ball Run, Zenitsu, Kurapika
  e Killua. Vídeos e épocas diferentes não permitem concluir causalidade.

Hipótese testável: um gancho com conflito/pista clara e ação
correspondente no primeiro quadro pode elevar a taxa que continua
assistindo. O alvo exploratório de **40% não é previsão de alcance**.

## Regras para FUTUROS episódios

| Etapa | Auditoria e planejamento | Restrição |
| --- | --- | --- |
| Gancho | Promessa ou consequência nos primeiros 1–3s, sugerir até 12 palavras | Não inventar fato canônico |
| Título | Testar 12–70 caracteres e promessa concreta | Não reescrever metadados publicados |
| Roteiro | Contexto, virada e resultado; evitar abertura genérica e CTA mecânico | Não dessicronizar voz já aprovada |
| Narração | Manter Edge TTS e revisar pronúncia | Não fabricar duração ou transcrição |
| Legenda | Até 3 palavras por bloco e tempos reais de voz | Não usar timing inventado |
| Miniatura | Capa original 9:16, texto de 2–5 palavras, rosto legível e hash | Não trocar por frame automático |
| Visual | Mostrar ação narrada no primeiro quadro, manter âncoras dos personagens | Zoom de câmera não é animação corporal |
| Duração | Priorizar teste curto 30–45s; 90s só em protocolo isolado | Não alterar limites rígidos de 60s de outros fluxos |
| Conteúdo | Mistério/contradição; escolha/consequência; curiosidade/habilidade | Não repetir episódios nem ignorar direitos |

A política exige pelo menos cinco vídeos comparáveis por variante
antes de promover uma hipótese, com janelas de idade 1h, 6h,
24h, 72h e 7d. Não transformar ausência de dado em zero.

## Proteções permanentes

- Preservar AGENTS.md, o registro de reservas, a pausa do lote de 50 Shorts,
  os perfis separados BR/EN e a autorização explícita de cada publicação.
- Manter personagens de anime identificáveis com referências visuais reais
  e revisão apropriada. Nunca substituir por silhuetas genéricas.
- Animação real exige camadas/poses; câmera suave não produz expressões,
  gestos ou malhas por si só.
- Não consumir APIs pagas, expor segredos, regenerar conteúdo antigo,
  postar Shorts ou mudar privacidade a partir do monitoramento.
- Mudanças de motor, regras rígidas de duração, direitos e publicação
  exigem QA e a autorização específica do criador.

## Verificação no projeto

Execute no repositório atualizado:

~~~powershell
python scripts/otaku_growth_autotune.py --output config/otaku-growth-active-v1.json --check
python -m pytest -q tests/test_otaku_growth_autotune.py tests/test_otaku_growth_v3.py tests/test_otaku_multicena_strategy_plan.py
~~~

Workflow:
https://github.com/HelioConde/AutoEditorVideo/actions/workflows/otaku-growth-autotune.yml

Perfil aplicado:
https://github.com/HelioConde/AutoEditorVideo/blob/main/config/otaku-growth-active-v1.json

Uma execução com testes verdes comprova a integridade da lógica,
mas NÃO uma melhora causal de audiência. O ganho deve ser medido depois.
