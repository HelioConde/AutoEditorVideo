# Kwai automático: GitHub -> Windows -> ADB Wi-Fi -> Samsung (08/11/2026)

## Arquitetura que foi implementada

O AutoEditorVideo permanece no GitHub e continua responsável pela geração.
O telefone Samsung SM-M236B (Android 14) já foi identificado pelo PC via
ADB Wi-Fi e scrcpy 5.0.1, conforme teste do proprietário.

Para enviar mídia ao aparelho SEM repetir comandos a cada vídeo, há dois
componentes independentes:

1. GitHub: fila de artefatos com MP4 aprovado no caminho
   config/kwai-adb-stage-queue.json.
2. Windows: scripts/kwai_github_pc_agent.py consulta essa fila somente em
   leitura, baixa MP4 de uma execução bem-sucedida de main via GitHub CLI,
   confirma SHA-256 e transfere pelo ADB ao Samsung. Se o SHA já estiver no
   telefone ou no recibo local, não duplica. Armazena recibos somente em
   LOCALAPPDATA/AutoEditorVideo/Kwai/staged-receipts.json.

O telefone recebe em /sdcard/Movies/AutoEditorVideo e uma atualização
do scanner de mídia é solicitada. Nenhum passo entra na conta, escolhe
a mídia na interface do Kwai ou pressiona "Publicar". Esta fase é
TRANSFERÊNCIA AUTOMÁTICA, ainda não PUBLICAÇÃO AUTOMÁTICA.

## Por que não conectamos um runner diretamente no repositório público?

HelioConde/AutoEditorVideo é PÚBLICO. Segundo a documentação de segurança
do GitHub, self-hosted runners são arriscados em repositórios públicos,
pois workflows maliciosos oriundos de PRs podem comprometer o PC.

https://docs.github.com/en/actions/reference/security/secure-use

Foi criado código experimental para usar um runner:
.github/workflows/kwai-android-local-runner-bridge.yml
Por segurança, as etapas que executariam no PC estão BLOQUEADAS enquanto
o repositório for público. **NÃO instale nem registre seu PC como runner
deste repositório público**. Futuramente, esse código poderá ser adaptado
para um repositório privado isolado, com proteções próprias.

O watcher local abaixo NÃO registra a máquina como runner, não aceita
código remoto para execução e não abre conexão de entrada.

## Instalação única no Windows 11

Pré-requisitos no computador que já pareou o Samsung:
- Python 3.11 ou superior no PATH ou em .venv/Scripts/python.exe.
- GitHub CLI (gh), já autenticado pelo próprio dono.
- ADB instalado no PATH ou em C:/platform-tools/adb.exe.
- Celular Samsung SM-M236B, Android 14+, com depuração Wi-Fi pareada,
  mesmo Wi-Fi do PC e aplicativo oficial Kwai com.kwai.video instalado.
- PC ligado e conta do Windows conectada. Nenhuma senha de Kwai será usada.

No PowerShell, dentro da pasta local do repositório:

    git pull --ff-only origin main
    .\kwai-github-celular.ps1 -Acao Diagnosticar

Esse diagnóstico consulta a fila e checa o aparelho; não envia nada.

Para deixar automático, com consulta periódica a cada 5 minutos:

    .\kwai-github-celular.ps1 -Acao InstalarAgendamento -ConfirmarAgendamento

O Task Scheduler executa uma tarefa a cada 5 minutos, no contexto
do usuário interativo que autorizou o ADB. Não requer senha GitHub/Kwai
no workflow nem privilégios de administrador.

Para acompanhar continuamente no terminal, SEM instalar tarefa:

    .\kwai-github-celular.ps1 -Acao Monitorar

Para remover o agendamento, sem apagar os vídeos já transferidos:

    .\kwai-github-celular.ps1 -Acao RemoverAgendamento -ConfirmarAgendamento

## Regras da fila

A fila está VAZIA por padrão: não existem vídeos aprovados para enviar
ao telefone apenas porque foram gerados no GitHub. Não publicar nem
transferir automaticamente qualquer vídeo privado ou conteúdo infantil.

Cada entrada autorizada exigirá os campos:
queue_id, channel, run_id, artifact_name, relative_video, sha256,
approved_for_local_stage, status.

Exemplo APENAS DOCUMENTAL, NÃO ADICIONAR SEM QA REAL:

    {
      "queue_id": "br-episodio-validado-001",
      "channel": "br",
      "run_id": 123456789,
      "artifact_name": "reel-final-validado",
      "relative_video": "video/final.mp4",
      "sha256": "(64 caracteres de hash SHA-256 verdadeiro)",
      "approved_for_local_stage": true,
      "status": "approved"
    }

Somente source run que terminou success em main do mesmo repositório,
com artefato exato, é elegível. O SHA local precisa corresponder ao
hash explicitamente aprovado na fila. Não inferir uma aprovação de QA
do sucesso técnico do CI. O agente não seleciona arquivos aleatórios,
não executa scripts contidos nos artefatos e não reutiliza tokens YouTube.

## O que falta para publicação completamente automática

1. Verificar se a conta Kwai está logada normalmente NO CELULAR.
2. Usar scrcpy para mapear as telas e os elementos acessíveis do Kwai,
   sem usar senhas/cookies nem coordenadas cegas; validar mudanças de UI.
3. Confirmar se o aplicativo e suas regras permitem automação de UI,
   inclusive identificando erros, seleção do MP4, legenda, capa, público
   e confirmação com recibo.
4. Automatizar depois de homologação, usando controle por estado
   e idempotência, sem contornar detecção ou desafios de segurança.
5. Integrar ao pipeline de QA para preencher a fila automaticamente
   SOMENTE para os vídeos aprovados e com direitos de uso.

A API oficial seria preferível para um publicador 100% cloud, mas sua
disponibilidade para a conta Kwai BR ainda não está confirmada.

## Arquivos no AutoEditorVideo

- kwai-github-celular.ps1 — configuração única e agendamento local
- scripts/kwai_github_pc_agent.py — consultas GitHub CLI sem executar código remoto
- scripts/kwai_adb_local_bridge.py — transferências ADB e hash verificável
- scripts/kwai_adb_artifact_gate.py — proveniência de runs do GitHub
- config/kwai-adb-stage-queue.json — fila sem credenciais
- tests/test_kwai_adb_github_bridge.py — regressões offline
- tests/test_kwai_github_pc_agent.py — regressões offline

Nenhum arquivo do Kwai, foto privada, chave ou token foi enviado a GitHub
como parte desta integração. Todo login permanece no app do dono.
