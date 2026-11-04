# Fofinhos Studio — proxy original em Go, sem Docker

## Descoberta e decisão

O projeto **10/chatgpt-codex-proxy** já é um servidor Go; a documentação upstream
explicita **Docker OU Go >= 1.26.9**. Portanto, *não precisamos converter ou
reescrever* o software para executá-lo nativamente.

- Código-fonte original: https://github.com/10/chatgpt-codex-proxy
- Commit fixado para o teste: \`1da5476e46ef62830d7016de2a931b0b8270a6c4\`
- Licença original: MIT; preservar atribuição.
- Fluxo sem Docker: Go build / Go test / iniciar binário / validar localhost.
- **Não** há autenticação de conta ChatGPT, imagem por IA ou upload de vídeo
  neste teste de infraestrutura.

## Execução verificada pelo workflow do GitHub

Workflow: \`.github/workflows/fofinhos-go-proxy-native.yml\`.

1. Checkout da branch testada do AutoEditorVideo.
2. Checkout do código Go original em **commit fixado** (não segue mudanças inesperadas de \`main\`).
3. Setup do Go com versão da dependência \`go.mod\`.
4. \`go test ./...\` no projeto upstream.
5. \`CGO_ENABLED=0 go build ... ./cmd/api\`.
6. Inicia o binário com \`PROXY_API_KEY\` **falsa** de teste,
   \`DATA_DIR\` temporário e sem nenhuma conta OAuth.
7. Verifica \`/health/live\`, acesso não autorizado (HTTP 401),
   acesso com chave errada (HTTP 401), autenticação com chave de teste (HTTP 200),
   e presença de zero contas.
8. Encerra o processo ao terminar o job.

O workflow não acessa **nenhum** Actions Secret, token OAuth, foto
infantil, cache de imagens ou endpoints de geração.

## Por que isso ainda não gera imagens na nuvem?

O segredo \`PROXY_API_KEY\` é apenas a chave de **cliente -> proxy**.
A autorização da conta é outro dado: o projeto original grava
\`DATA_DIR/accounts.json\`, com tokens OAuth e dados da conta.

No Docker, \`DATA_DIR\` está em volume próprio; na execução nativa, o
diretório configurado inicia vazio. O runner padrão do GitHub Actions é
temporário; sua pasta desaparece após o job. Assim, iniciar o Go sem Docker
não traz automaticamente as sessões de uma instalação anterior.

**Não** enviar \`accounts.json\`, refresh tokens ou fotos privadas a commits,
artefatos, logs de Actions, issues ou pull requests. Não clonar/capturar
sessões silenciosamente do Docker, e não copiar cookies para uma workflow
pública. Antes de permitir geração de imagens reais em GitHub Actions,
é preciso projetar e autorizar uma estratégia de identidade, armazenamento
criptografado e cache privado, com rotação e revogação de acesso.

O proxy é um projeto comunitário baseado em APIs privadas não documentadas
da OpenAI; o suporte e as condições de acesso podem mudar. Não pressupor
gratuidade ou disponibilidade de modelos.

## Caminho seguro para evoluir o editor

Primeiro validar Go e execução local no runner sem credenciais reais.
Segundo definir onde as contas e referências privadas serão guardadas
sem exposição pública. Terceiro executar testes de conexão sem geração
e apenas após autorização explícita testar uma única imagem com cota
controlada. Os testes de interface/Remotion independem dessa etapa
e já funcionam no GitHub.

**Não** usar a antiga proposta de expor o proxy do Windows por túnel
público como pré-requisito: o binário Go pode iniciar dentro do próprio
runner, desde que sua autenticação seja provisionada com segurança.
