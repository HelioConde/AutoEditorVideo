# Objetivo: publicar vídeos do AutoEditorVideo no Kwai Brasil

Status 08/11/2026: **prioridade exclusiva Kwai**, não TikTok.

## Testes comprovados

Android 14 no GitHub Actions já funciona, com ADB e transferência íntegra de MP4:
https://github.com/HelioConde/AutoEditorVideo/actions/runs/42466736151

Teste específico Kwai BR com Android 14 Google Play:
https://github.com/HelioConde/AutoEditorVideo/actions/runs/42467580687

Resultados: Android inicializado, Play Store instalada, intento da página oficial do Kwai enviado, vídeo sintético copiado com SHA-256 correto. **Captura mostra a tela de LOGIN da Google Play, não a ficha de instalação do Kwai.** Nenhuma conta foi usada. Kwai (com.kwai.video) não foi instalado. Publicação pelo aplicativo ainda **NÃO comprovada**. Artefato: kwai-brazil-android-google-play-feasibility-20261108.

## Fontes oficiais

Aplicativo Kwai Brasil: https://play.google.com/store/apps/details?id=com.kwai.video&gl=BR

Ajuda do Kwai descreve publicação pelo botão da câmera, seleção pelo álbum e Compartilhar: https://www.kwai.com/support/video/how-do-i-post-a-video

A documentação da plataforma chinesa Kuaishou descreve API OAuth user_video_publish, upload e publicação: https://open.kuaishou.com/platformDocs/openAbility/contentManagement/createAVideo

**Não presumir que a API chinesa concede acesso de publicação à conta Kwai brasileira.** É preciso confirmação do operador da plataforma e credenciamento OAuth válido.

## Próximos passos para publicação real

Prioridade: investigar e solicitar acesso à API oficial para Kwai Brasil. Com autorização, implementar módulo independente com OAuth, idempotência, verificações de canal/visibilidade, relatórios de uploads e confirmação do vídeo antes de registrar sucesso.

Alternativa: testar o Kwai oficial em um dispositivo Android próprio com login feito localmente pelo dono. Um runner self-hosted local e Android via ADB podem auxiliar, mas precisam de instalação, conexão física e aprovação expressa do criador. O runner hospedado do GitHub não acessa o celular real.

Não colocar senhas, cookies ou credenciais pessoais Google/Kwai no GitHub Actions. Não instalar APKs de fontes desconhecidas, nem contornar autenticação, captcha, detecção de emuladores ou limites das plataformas. Não marcar testes de inicialização Android como evidência de publicação real.

## Arquivos específicos Kwai

- .github/workflows/kwai-android-playstore-feasibility-20261108.yml
- scripts/kwai_android_playstore_probe_20261108.py
- tests/test_kwai_android_playstore_probe_20261108.py
- config/kwai-android-playstore-policy-20261108.json

O teste não fez upload real nem alterou os canais ou vídeos existentes.


## Conexão planejada: OAuth Kwai com GitHub Secrets (08/11/2026)

Sim, o AutoEditorVideo pode armazenar tokens OAuth oficiais em GitHub Actions
Secrets, do mesmo modo que guarda tokens autorizados do YouTube. Contudo,
**Secrets não são um mecanismo de login**: receber uma senha do aplicativo ou
um cookie Android não cria uma integração oficial de publicação.

Documentação oficial da plataforma Kuaishou (China):
- Web OAuth: https://open.kuaishou.com/platformDocs/develop/web-app.html
- Troca e renovação de tokens: https://open.kuaishou.com/platform/openApi?menu=13
- Publicação: https://open.kuaishou.com/platformDocs/openAbility/contentManagement/createAVideo

A API documentada exige a aprovação de um aplicativo desenvolvedor e os
identificadores app_id e app_secret. Para publicar, o titular autoriza o
escopo user_video_publish. O access_token documentado tem validade de 48h;
a renovação pode substituir o refresh_token anterior, exigindo rotação
segura e sincronizada do Secret. **Ainda não foi confirmado se esse
programa OAuth atende às contas Kwai do Brasil.**

### Estrutura separada e segura planejada

Repositório: HelioConde/AutoEditorVideo.

Novo GitHub Environment proposto: kwai-private-publish,
com deployment branch policy restrita EXCLUSIVAMENTE à branch main.
Ele deve ser configurado e validado ANTES de qualquer credencial ser enviada.
Não usar nem modificar o Environment do YouTube como atalho.

Secrets planejados, ainda NÃO configurados:
- KWAI_APP_ID
- KWAI_APP_SECRET
- KWAI_OAUTH_TOKEN_JSON

O consentimento OAuth deverá ocorrer no navegador do titular,
com callback autorizado para a aplicação cadastrada. Não copiar senhas,
códigos SMS, códigos de autenticação ou cookies para o repositório, conversa
ou GitHub. As credenciais não devem aparecer em commits nem logs.

### Estado real

- Disponibilidade da API de publicação para Kwai Brasil: NÃO VALIDADA.
- Aplicação de desenvolvedor Kwai Brasil aprovada: NÃO CONFIRMADA.
- Conta OAuth Kwai conectada: NÃO.
- Tokens salvos em GitHub Secrets: NÃO.
- Automação de publicação Kwai: DESATIVADA.

Configuração sem segredos:
config/kwai-br-github-oauth-readiness.json.
Validador offline: scripts/kwai_github_oauth_readiness.py.
Regressões: tests/test_kwai_github_oauth_readiness.py.

A etapa de conexão real deve continuar BLOQUEADA até confirmação da
plataforma e concessão explícita de credenciais oficiais de aplicativo.
Depois, implementar a autenticação autorizada, verificação de conta, rotação
atômica de refresh_token e publicação com reconciliação de IDs e status.
