# Instagram Reels no AutoEditorVideo — preparação segura (08/11/2026)

**Status: infraestrutura OFFLINE preparada; nenhuma conta conectada, nenhum
token configurado e nenhuma publicação realizada.** Esta integração é
independente do YouTube e do teste Kwai.

## Método escolhido

Instagram API with Instagram Login (não Facebook Login). Suporta contas
profissionais Business / Creator, com permissões
instagram_business_basic e instagram_business_content_publish.
Não é necessário vincular uma Página Facebook nesse método.

Documentação oficial Meta:
- https://developers.facebook.com/docs/instagram-platform/instagram-api-with-instagram-login/
- https://developers.facebook.com/docs/instagram-platform/content-publishing/
- https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api

## O que foi implementado

- Configuração fail-closed: config/instagram-api-readiness.json
- Planejador estático e guard de GitHub Environment:
  scripts/instagram_api_readiness.py
- Testes sem chamadas à API: tests/test_instagram_api_readiness.py
- Workflow offline e manual:
  .github/workflows/instagram-reels-safe-readiness.yml
- Manifesto de disparo de CI:
  config/instagram-reels-preflight-launch-20261108.json

A configuração reconhece os nomes de produção br, en, games, kids e alchemy.
Cada um está sem Instagram User ID até a identidade ser verificada via API
e consentimento. Não presumir que os cinco canais YouTube têm contas
Instagram equivalentes.

Rodar inspeção local (sem segredos): python scripts/instagram_api_readiness.py --action inspect

## Como o dono ativa futuramente (sem compartilhar senha aqui)

1. Confirmar Instagram como Criador ou Comercial.
2. Abrir https://developers.facebook.com/apps/ e criar aplicação
   para Instagram API with Instagram Login. Configurar o caso de uso
   de gerenciamento de conteúdo Instagram conforme o painel da Meta.
3. Adicionar a conta profissional como tester/developer do app enquanto
   estiver em modo de desenvolvimento, quando aplicável. Concluir
   os requisitos de verificação/autorizações que o painel exigir.
4. Cadastrar URI de redirecionamento HTTPS sob seu controle; configurar
   escopos instagram_business_basic e instagram_business_content_publish.
5. Fazer OAuth pelo navegador do titular, sem colocar senhas, sessões,
   códigos 2FA ou access tokens em conversas, arquivos públicos ou logs.
6. Consultar o Instagram User ID efetivamente autorizado, confirmar o
   destino e associar explicitamente ao canal certo; não copiar o YouTube ID.
7. Criar o ambiente GitHub instagram-private-publish SEPARADO de
   youtube-private-upload e dos demais, com deployment branches contendo
   SOMENTE main e, se possível, revisores obrigatórios.
8. Depois de validação local, armazenar Secrets próprios desse ambiente:
   INSTAGRAM_APP_ID, INSTAGRAM_APP_SECRET, INSTAGRAM_OAUTH_TOKEN_JSON.
   Nada disso está criado ou enviado ainda. Só autorizar escrita de
   Secrets após confirmar a proteção exata do Environment no GitHub.
9. Configurar HTTPS público estável para o MP4 e, se utilizado, a capa
   renderizada pelo AutoEditorVideo. GitHub Actions artifacts NÃO são
   links públicos adequados ao media fetch da Meta. Nunca tornar privadas
   as fotos de crianças, dados pessoais, músicas sem licença ou vídeos
   não aprovados simplesmente para satisfazer essa exigência.
10. Implementar um workflow futuro separado para teste autenticado,
    criação de container REELS, polling de status_code (FINISHED) e
    media_publish com revisão explícita de QA e destino.
11. Guardar recibos de criação/publicação e evitar duplicação após erros
    de rede; nunca supor que erro implica ausência de publicação.
12. Planejar renovação de tokens conforme a modalidade Meta autorizada.
    Tokens expirados não são segredos permanentes. Não reutilizar o
    token OAuth dos canais do YouTube.

## Fluxo futuro de vídeo

AutoEditorVideo -> QA / direitos / legenda / capa -> MP4 e HTTPS público
-> POST graph.instagram.com/v25.0/{ig_id}/media
   (media_type=REELS, video_url, caption)
-> consultar container status até FINISHED
-> POST graph.instagram.com/v25.0/{ig_id}/media_publish
   (creation_id do container)
-> conferir id/permalink e registrar recibo.

IMPORTANTE: Em Instagram API não há "upload privado de teste" equivalente
a vídeo privado do YouTube. Criar container não é publicar; media_publish
é uma ação efetiva, que requer autorização específica.

O API client desta etapa é deliberadamente OFFLINE e não executa POSTs.
O login OAuth e o workflow de produção serão implementados após haver
app Meta e conta autorizada; não alegar que eles já funcionam.

## Repetir os testes seguros

Acessar o repositório no GitHub > Actions >
AutoEditorVideo - Instagram Reels OAuth preparation (no publishing) >
Run workflow, branch main, marcar confirm_safe_offline_only.
Os resultados ficam em artifact instagram-api-readiness-no-secrets.

## Privacidade e outros canais

Não alterar Secrets nem publicação do YouTube, Kwai e TikTok.
NÃO publicar automaticamente conteúdos do canal infantil nem materiais
com referências privadas. Antes de ativar Kid/BR/EN/Games/Alchemy para
Instagram, revisar direitos de imagem/música, a classificação apropriada,
a identidade exata da conta e a visibilidade real na plataforma.
