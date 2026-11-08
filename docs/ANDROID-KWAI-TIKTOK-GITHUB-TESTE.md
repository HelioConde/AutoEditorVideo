# Android no GitHub Actions — teste seguro para AutoEditorVideo

Status: teste técnico, não integração de publicação.

## Arquivos
- .github/workflows/android-14-safe-publishing-feasibility-smoke.yml
- scripts/android_emulator_safe_smoke.py
- config/android-ci-publication-feasibility.json
- tests/test_android_emulator_safe_smoke.py

## Procedimento seguro
1. Validar a política, as proteções e testes unitários sem contas sociais.
2. Iniciar Android 14 API 34, arquitetura x86_64, imagem google_apis em runner Ubuntu com KVM e a ação ReactiveCircus android-emulator-runner.
3. Conferir boot completo e ADB.
4. Gerar vídeo sintético FFmpeg de dois segundos e enviá-lo para /sdcard/Movies no emulador.
5. Confirmar SHA-256 idêntico no runner e Android.
6. Capturar a tela inicial e armazenar apenas o relatório, imagem e MP4 de demonstração em artefatos temporários.

**Nenhum login, token, APK TikTok/Kwai, vídeo real, publicação ou alteração de canal faz parte do teste.** Passar nesse teste NÃO prova que o app TikTok ou Kwai consegue publicar no emulador.

Para repetir: Actions > AutoEditorVideo - Android 14 emulator safe smoke test > Run workflow (main) > marcar confirm_no_publication.

## Integração futura recomendada
- TikTok: Content Posting API com aprovação do escopo video.publish, consentimento OAuth e auditoria exigida para publicação pública. https://developers.tiktok.com/docs/en/content-posting-api-get-started
- Kwai: a Kuaishou disponibiliza documentação da API user_video_publish, mas isso não comprova acesso da conta Kwai brasileira. Validar credenciamento e disponibilidade oficial. https://open.kuaishou.com/platformDocs/openAbility/contentManagement/createAVideo
- Não usar automação para contornar login, restrições de emuladores, captcha ou limites.
- Não armazenar senhas, cookies ou tokens de conta no cache/artefato do GitHub.
- Antes de enviar conteúdo real, fazer uma implementação independente, com OAuth permitido, consentimento e reconciliação dos IDs para evitar duplicação.

O runner Android é efêmero e sua instalação precisa acontecer em cada execução; podem ocorrer falhas de KVM, SDK ou rede que não comprovam falha das APIs sociais.
