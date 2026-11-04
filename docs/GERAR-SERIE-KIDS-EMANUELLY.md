# Gerador de Emanuelly — quatro Shorts Kids com foto de referência

## Escopo

Produção LOCAL do EP 1 da série Emanuelly e seus Amigos de Pelúcia, dividido em quatro Shorts (máximo de 60 segundos). O roteiro completo é preservado em docs/KIDS-EMANUELLY-SERIE-BIBLIA-V1.md e as quatro partes estão em conteudos/kids-emanuelly-ep01-shortserie-v1.json.

**A foto do elenco é obrigatória para gerar cada imagem.** O arquivo privado não é versionado no GitHub: fica somente em assets/referencias-privadas/emanuelly-elenco.png, com proteção explícita no .gitignore. Cada nova imagem é solicitada ao endpoint de edição do Codex Proxy em http://127.0.0.1:8080/v1/images/edits, com o PNG da referência codificado na requisição. O proxy pode encaminhar a foto ao provedor configurado. Execute somente se autorizar esse envio. Sem suporte a edições, o programa falha — não produz imagem genérica de substituição.

## Primeira instalação no Windows

    cd "C:\Users\helio\Documents\arquivo-otaku-github"
    git pull --ff-only origin main

Instale a foto de uma das duas formas:

**A. ZIP privado:** baixe o arquivo referencia-emanuelly-autoeditorvideo.zip fornecido na conversa e, após salvá-lo em Downloads, execute:

    Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\referencia-emanuelly-autoeditorvideo.zip" -DestinationPath (Get-Location) -Force

A extração cria assets/referencias-privadas/emanuelly-elenco.png na pasta do projeto. Não adicione essa foto ao GitHub público.

**B. Imagem salva no computador:**

    .\gerar-historia-kids.ps1 -Acao InstalarReferencia -Referencia "C:\Users\helio\Downloads\minha-foto.png"

Para substituir uma referência já instalada, acrescente -Refazer. O arquivo antigo é preservado em histórico; imagens antigas não são reutilizadas como se fossem dessa nova referência.

## Comandos PowerShell

    # Apenas mostra o plano e quantos quadros faltam, sem chamadas de IA
    .\gerar-historia-kids.ps1 -Acao Planejar -Parte Todas

    # Gera a Parte 1 inteira (quadros, locução e MP4 local)
    .\gerar-historia-kids.ps1 -Acao Gerar -Parte 1 -MaxChamadas 9

    # Abre o MP4 local no player padrão
    .\gerar-historia-kids.ps1 -Acao Abrir -Parte 1

    # Continua o EP1, respeitando os limites de novas imagens
    .\gerar-historia-kids.ps1 -Acao Gerar -Parte 2 -MaxChamadas 10
    .\gerar-historia-kids.ps1 -Acao Gerar -Parte 3 -MaxChamadas 9
    .\gerar-historia-kids.ps1 -Acao Gerar -Parte 4 -MaxChamadas 9

    # Inspeciona o status dos quatro vídeos
    .\gerar-historia-kids.ps1 -Acao Verificar -Parte Todas

Total previsto: 37 quadros de IA, antes do cache. O parâmetro MaxChamadas é um TETO de chamadas de imagens por execução, não uma estimativa de custo. Se o orçamento for insuficiente, o programa não faz nenhuma chamada de IA. Modelo padrão: gpt-image-1.5, com alternativa gpt-image-2 quando suportado.

Execução por etapas:

    .\gerar-historia-kids.ps1 -Acao Imagens -Parte 1 -MaxChamadas 9
    .\gerar-historia-kids.ps1 -Acao Voz -Parte 1
    .\gerar-historia-kids.ps1 -Acao Renderizar -Parte 1

O usuário pode executar uma única parte primeiro para avaliar a fidelidade dos personagens. Imagens e narração já geradas podem ser reutilizadas sem novas chamadas se os hashes conferirem. Para recriar todas as imagens de uma parte, use Imagens -Refazer com orçamento suficiente; versões anteriores são preservadas.

## Requisitos locais

Python e .venv configurado com Pillow, Numpy, requests e edge-tts. FFmpeg e FFprobe disponíveis no PATH. Node/npm e Remotion instalados em motion-remotion (npm.cmd install). Codex Proxy configurado com credenciais válidas e um modelo que suporte images/edits. As requisições podem consumir cotas, dinheiro e tempo conforme o provedor configurado.

## Fluxo de produção

1. Validar imagem de referência privada e calcular SHA-256.
2. Gerar um quadro novo por fala, com a foto como entrada REAL da edição. O modelo deve preservar Emanuelly e os bichinhos, seus traços e seu estilo, sem mostrar Fofinho fora do ovo antes do nascimento ou apresentar as gêmeas prematuramente.
3. Gerar voz portuguesa pt-BR-FranciscaNeural em falas separadas, com pausas reais e tempo para respostas. Proteger o limite de áudio de 59,2 segundos; se não couber, revisar texto em vez de acelerar artificialmente.
4. Gerar legendas a partir dos tempos reais da voz, e quadros sincronizados com os beats. Durante os silêncios, não mostrar legenda prolongada.
5. Renderizar em Remotion, 1080x1920 30 FPS, com transições suaves e partículas animadas independentemente das imagens. **Não é rigging articulado dos personagens**: a animação de braços/cabeça depende de imagens distintas e de novas técnicas de rigging em versões futuras.
6. Verificar MP4 com FFprobe, presença de áudio, 9:16 e duração <= 60s. Armazenar QA contendo hashes da imagem de referência, imagens geradas, voz e vídeo.
7. Preservar versões antigas e acrescentar o MP4 novo à biblioteca Kids caso a biblioteca tenha sido inicializada anteriormente.

## Pastas dos resultados

    assets\gerados\kids-emanuelly\
      kids-emanuelly-ep01-p01-ovo-azul\
        quadros\quadro-01.png
        quadros\quadro-01.json
        ...
        narracao.mp3
        marcacoes-voz.json
        final.mp4
        qa-local.json
        historico-imagens\
        historico-renders\

O MP4 não contém a foto de origem nem a copia na pasta pública. A foto só é usada como entrada da edição de imagens. Se a consistência visual entre quadros não for boa, corrigir prompt/quadros e regenerar; hashes comprovam proveniência, não semelhança facial. Revisar o vídeo completo antes de qualquer publicação.

## Segurança e status

Nenhum comando cria canal, autentica no YouTube ou publica. O público previsto é Made for Kids, sem pedido de comentários, inscrições ou compra. A referência e eventuais dados pessoais devem ser tratados como privados. O uso da imagem em serviço remoto depende da escolha do usuário.

Os testes no GitHub simulam proxy, TTS e PowerShell, sem serviços externos e sem render real. O commit não cria nenhum MP4: a geração ocorre somente quando os comandos forem executados no Windows.
