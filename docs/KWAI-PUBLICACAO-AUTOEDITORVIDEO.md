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
