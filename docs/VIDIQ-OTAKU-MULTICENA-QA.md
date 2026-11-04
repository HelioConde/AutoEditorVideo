# Otaku Multicena — aprendizados dos 8 check-ins do vidIQ (2026-11-03)

**Origem:** oito relatórios de forecast fornecidos pelo criador, não métricas
consultadas diretamente no YouTube Studio. Forecast não garante alcance.
Não comparar Shorts com idades diferentes sem normalizar o tempo publicado.

| Short | Views na captura | Projeção dia 14 | Problema observado no relatório |
|---|---:|---:|---|
| [VfliGg3N4rU](https://youtube.com/shorts/VfliGg3N4rU) | 474 | ~607 | Personagem estático 0–6,5s; texto pequeno |
| [mP34eFfMIRI](https://youtube.com/shorts/mP34eFfMIRI) | 1.169 | ~1.300 | Abertura pouco dinâmica |
| [ZKkfQejnYaA](https://youtube.com/shorts/ZKkfQejnYaA) | 371 | ~573 | Xadrez estático 0–6s; texto atrasado, contraste |
| [yTAyi97LKoI](https://youtube.com/shorts/yTAyi97LKoI) | 191 | ~293 | Misa estática; texto fragmentado; interação tarde |
| [Zg2mSwipw3I](https://youtube.com/shorts/Zg2mSwipw3I) | 424 | ~629 | Light estático 0–4s; texto cobrindo personagem |
| [w6eSdUGk6aE](https://youtube.com/shorts/w6eSdUGk6aE) | 3 | ~5 | Light/Ryuk quase imóveis por 15s |
| [wZ0Kx0UyB0s](https://youtube.com/shorts/wZ0Kx0UyB0s) | 2 | ~6 | Imagem estática 0–4,7s; texto lento/sobre personagens |
| [Jwd_BUp9Y98](https://youtube.com/shorts/Jwd_BUp9Y98) | 2 | ~9 | Abertura estática; texto no torso e atrasado |

**Padrões:** 8/8 mencionam pouco movimento ou variedade na abertura;
6/8 mencionam problemas de texto/legenda; 1/8 pede interação de dois
personagens mais cedo. Isso é feedback editorial útil, **não demonstra** que
o algoritmo penaliza formalmente imagens estáticas, nem que as previsões se cumprirão.

## Correções de engenharia entregues

1. **Remotion master e legado (corrigido após feedback do criador):**
   os jump cuts virtuais em 1,25s, 2,45s e a cada 2,7s causaram
   desconforto e foram **removidos**. O novo movimento é um zoom in/out
   contínuo, centralizado e de pequena amplitude. Os personagens com
   máscaras RGBA seguras têm movimento de corpo mais perceptível, sem
   esticar rosto/membros. Arte plana só faz zoom; não fingir movimento real.
   O QA registra quantas cenas permitem movimento de personagem.
2. **Legendas:** Remotion master usa grupos de 2–3 palavras com timestamps
   de voz reais; o legado também agrupa marcações existentes em até três
   palavras, destacando a palavra falada. Fundo escuro e fonte grande na
   zona inferior em vez de cobrir o rosto.
3. **Arte das próximas produções:** prompts iniciais priorizam a ação ou
   interação explicitamente narrada, sem inventar cenas canônicas nem reescrever
   roteiros. Isso **só afeta imagens futuras** e precisa do orçamento de IA
   escolhido pelo usuário, não gera imagens automaticamente.
4. **Cache:** assinatura SHA-256 do renderizador invalida um MP4 local antigo
   quando a câmera, legendas ou compositor mudarem, mesmo que o Edge TTS não
   tenha mudado. O cache de imagens e narração permanece íntegro.
5. **Proteções:** nenhum vídeo já publicado é apagado ou reenviado.
   `-Publicar` segue sendo uma autorização explícita; duração final
   <= 60s validada com ffprobe; uma cena/arte reprovada continua bloqueada.

## Validar no Windows sem publicar

Na pasta do repositório:

```powershell
git pull --ff-only origin main
Push-Location .\motion-remotion
npm.cmd run typecheck
npm.cmd run test:qa
Pop-Location

.\.venv\Scripts\python.exe -m pytest -q tests/test_legendas_precisas.py tests/test_render_fingerprint.py tests/test_vidiq_editorial_qa.py

# Opcional: prévia de um episódio existente com arte já em cache.
# Sem IA de imagem nova, sem upload, mas renderiza MP4 localmente.
.\criar-publicar-short.ps1 -Id 401-jujutsu-kaisen-ep01 -VozMotor edge -Modelo gpt-image-1.5 -Perfil equilibrado -MaxChamadas 0 -Refazer
```

Se estiver faltando arte aprovada, o último comando **para sem publicar**.
O render original pode ser reaproveitado apenas como referência; o sistema
não pode atualizar um Short existente no YouTube substituindo seu arquivo.

### QA antes do próximo vídeo

- Conferir quadros em 0,0s / 1,3s / 2,5s / 5,0s na prévia
  vertical: zoom deve mudar suavemente, sem saltos, e não cortar cabelo/mãos.
- Conferir legendas de 2–3 palavras em fundo contrastado, na zona inferior.
  Validar o primeiro segundo e uma frase longa contra a voz real.
- Confirmar ação principal/objeto relevante no primeiro quadro **quando
  pertinente ao roteiro**, não retrato passivo.
- Conferir MP4 de até 60,000 segundos e canal/visibilidade antes de qualquer upload.
- Comparar a retenção de quem permanece e compartilhamentos dos próximos
  Shorts com os anteriores em janelas equivalentes de 24h e 72h.

A melhoria é uma **hipótese de produção para teste**, não uma promessa de
visualizações ou monetização. Não reupar vídeos existentes indiscriminadamente.
