# VoiceStudio opcional para o Otaku Multicena

O Edge TTS continua **padrao** e nao foi removido. A integracao apenas adiciona
`-VozMotor voicestudio` ao fluxo brasileiro do `criar-publicar-short.ps1`.

## Primeira instalacao

1. Instale a versao Windows x64 de https://github.com/debpalash/VoiceStudio/releases/latest
2. Abra o VoiceStudio e configure um modelo de texto-para-fala que suporte PT-BR.
3. Instale tambem um modelo de transcricao **Whisper com timestamps por palavra**.
   Sem ASR, a API `/v1/audio/transcriptions` retorna 409 e o teste para,
   porque nosso Remotion exige legendas com tempos reais.
4. Deixe o backend VoiceStudio aberto em `http://127.0.0.1:3900`.
   Em Integrations -> VoiceStudio API, confira a URL local. O adaptador
   so aceita localhost / 127.0.0.1 / ::1, sem enviar arquivos a servidores remotos.
5. O programa pode funcionar na CPU em placas antigas (mais lento); use modelos leves.
   Um modelo TTS diferente pode exigir a escolha de um novo `-ModeloVoiceStudio`.

## Primeiro teste: gera somente a narracao

Abra o PowerShell na pasta do projeto:

```powershell
cd "$HOME\Documents\arquivo-otaku-github"
git pull --ff-only origin main
.\testar-voz-studio.ps1 -Id 401-jujutsu-kaisen-ep01 -CompararEdge
```

Saidas em `assets/gerados/shorts-animados/401-jujutsu-kaisen-ep01/`:
- `voz-voicestudio-<hash>.mp3` — teste local;
- `legendas-voicestudio-<hash>.ass` — palavras cronometradas por ASR;
- `voz-master.mp3` e `legendas.ass` — arquivos Edge TTS (criados/reutilizados ao usar `-CompararEdge`).

**Nao ha imagens, MP4, publicacao ou upload no teste.** Os arquivos VoiceStudio
ficam separados dos existentes. O cache e indexado por roteiro, modelo e voz.
Nao sao geradas legendas com temporizacao artificial: na falta do modelo ASR
ou se a transcricao divergir do roteiro, o teste e bloqueado.

Para outro modelo/perfil (consultar `GET /v1/models` e `GET /v1/audio/voices`
no backend local):

```powershell
.\testar-voz-studio.ps1 -Id 401-jujutsu-kaisen-ep01 -ModeloVoiceStudio "tts-1" -PerfilVoiceStudio "default"
```

## Erro HTTP 403 durante o primeiro teste

Abrir `http://127.0.0.1:3900/v1/audio/speech` no navegador faz um
**GET** e pode responder 404 Not Found. Isso nao testa a API TTS:
a rota valida e `POST /v1/audio/speech` com JSON.

Se o teste retornar 403, a integracao agora mostra o codigo e o
motivo conhecido. Os casos comuns sao:

- **model_licence_required** (licenca pendente): abra o VoiceStudio,
  acesse o Catalogo de modelos, escolha o motor OmniVoice e abra
  **Licenca**. Leia os termos e aceite somente se seu teste for
  permitido; se o Whisper estiver bloqueado, faca o mesmo com o ASR.
  Nenhuma licenca e aceita pelo script.
- **Request refused / unrecognized host** (acesso negado): use a API
  em `http://127.0.0.1:3900` e confira configuracao do VoiceStudio.
  O adaptador desabilita proxies de ambiente para trafego local
  (`HTTP_PROXY`, `HTTPS_PROXY`), mantendo audio e roteiro no PC.
- **409 / ASR model missing**: instale e ative um motor Whisper para
  transcrever e sincronizar as legendas.

Depois da revisao das licencas e instalacao do modelo, execute:

```powershell
cd "$HOME\Documents\arquivo-otaku-github"
git pull --ff-only origin main
.\testar-voz-studio.ps1 -Id 401-jujutsu-kaisen-ep01 -CompararEdge
```

**Importante:** os pesos padrao OmniVoice possuem restricao nao
comercial. Aceitar a licenca nao autoriza monetizar Shorts. O teste e
somente privado e comparativo; para publicar ou monetizar, selecione
outro modelo cujos termos autorizem esse uso. Em caso de 403 persistente,
envie o novo erro com o codigo retornado. Nao exponha chaves, tokens
nem dados de conta.

## Producao opcional, SEM PUBLICAR

Depois de validar a voz e as licencas dos pesos baixados:

```powershell
.\criar-publicar-short.ps1 -Id 401-jujutsu-kaisen-ep01 -VozMotor voicestudio -Modelo gpt-image-1.5 -MaxChamadas 45
```

O pipeline completo pode gerar imagens IA e consumir cota. Sem `-Publicar`,
nao envia ao YouTube. Para voltar ao motor original, omita `-VozMotor`
ou use `-VozMotor edge`. No fluxo principal, quando o audio de origem e
diferente, o MP4 deve ser renderizado novamente e a escolha da voz e
registrada em `build-voz-<perfil>.json`; nao se reutiliza MP4 com voz errada.

O modo `-Publicar` continua exigindo consentimento explicito e credenciais
OAuth corretas para o canal brasileiro. O primeiro teste **nao o utiliza**.

## Licencas e direitos

VoiceStudio e AGPL-3.0, mas cada modelo/peso tem licenca propria. O modelo
OmniVoice padrao, por exemplo, identifica pesos CC-BY-NC. Nao use um modelo
marcado como nao comercial em videos destinados a monetizacao sem uma permissao
adicional adequada. Use somente vozes proprias, licenciadas ou com consentimento.
O primeiro teste e para comparar qualidade, nao para publicacao.
