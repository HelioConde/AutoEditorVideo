# Emanuelly e Fofinho — imagens fixas para as quatro partes

Biblioteca oficial: o MESMO jardim em 4 ângulos, o MESMO quarto em 4 ângulos,
um ovo azul com as gotinhas preservadas, caminha, versões da casca
e o mesmo Fofinho de pelúcia azul em poses diferentes.

## Imagens que precisam ser salvas no Windows

Cenários e ovo intacto (já desenhados anteriormente na conversa):

    jardim-01.png
    jardim-02.png
    jardim-03.png
    jardim-04.png
    quarto-01.png
    quarto-02.png
    quarto-03.png
    quarto-04.png
    ovo-azul.png

Recursos adicionais isolados e transparentes (criar/importar conforme necessário):

    caminha-ovo.png
    ovo-rachado.png
    ovo-aberto.png
    fofinho-azul.png
    fofinho-miando.png
    fofinho-patinhas.png
    fofinho-aconchegado.png
    gotinha-agua.png

As oito imagens adicionais têm origem oficial registrada:
caminha derivada do quarto-01; cascas e gotinhas derivadas do ovo-azul;
Fofinho oficial derivado da referência privada de Emanuelly + Fofinho;
as poses de Fofinho derivadas do Fofinho oficial. Se uma origem mudar,
a versão derivada é invalidada pelo SHA-256 para não trocar de identidade
no meio da série.

As imagens dos cenários não podem conter personagens, ovo ou textos
embutidos. O ovo e os bichinhos devem ter transparência real.

## Storyboard por parte

| Short | Sequência | Recursos principais |
|---|---|---|
| Parte 1 | Ovo no jardim (sem Manu) → encontro → levar para casa → caminha → toc toc | Jardim, quarto, ovo fechado, caminha, poses de Manu |
| Parte 2 | Ovo balança → casca racha → casca abre → nasce Fofinho → primeira gotinha | Quarto, caminha, ovo fechado/rachado/aberto, Fofinho e gotinha |
| Parte 3 | Fofinho brinca com 1–3 gotas → brincadeiras no jardim → carinho | Mesmo Fofinho, gotinha repetida, jardim e quarto |
| Parte 4 | Fofinho consola Manu → gota no nariz → abraço → dormir → brilho de ovos futuros | Mesmo Fofinho, pose aconchegada, quarto, jardim e gotinha |

**Regra obrigatória:** Fofinho só aparece na Parte 2, cena 6. Antes,
Manu e ovo azul. Fofinha Arco-Íris, Fofinha Rosa, Raposo e Porco-espinho
não podem aparecer em nenhuma dessas quatro partes.
As gêmeas nascem um ano após Fofinho. A cena final da Parte 4 usa
somente brilhos abstratos de ovos futuros, sem revelar personagens.

## Comandos PowerShell

    cd "C:\Users\helio\Documents\arquivo-otaku-github"
    git pull --ff-only origin main

    # Lista TODAS as imagens, poses e ações para os quatro vídeos:
    .\animar-emanuelly.ps1 -Acao Catalogo -Parte Todas

    # Relatório indicando quais imagens e poses faltam por parte:
    .\animar-emanuelly.ps1 -Acao Planejar -Parte Todas

    # Instalar as imagens já aprovadas que você salvou, mesmo que
    # a pasta contenha somente algumas das imagens oficiais:
    .\animar-emanuelly.ps1 -Acao InstalarLote -Pasta "$env:USERPROFILE\Pictures\Emanuelly\Referencias"

    # Importar uma imagem individual:
    .\animar-emanuelly.ps1 -Acao Instalar -Recurso ovo-rachado -Arquivo "C:\Imagens\ovo-rachado.png"

    # Gerar APENAS uma imagem que esteja faltando, usando sua referência:
    .\animar-emanuelly.ps1 -Acao GerarImagens -Recurso ovo-rachado -MaxChamadas 1
    .\animar-emanuelly.ps1 -Acao GerarImagens -Recurso fofinho-azul -MaxChamadas 1

    # Ação opcional para as variantes faltantes do nascimento:
    .\animar-emanuelly.ps1 -Acao Planejar -Parte 2
    .\animar-emanuelly.ps1 -Acao GerarImagens -Parte 2 -MaxChamadas 7

    # Preparar e renderizar as quatro partes quando todas estiverem prontas:
    .\animar-emanuelly.ps1 -Acao Verificar -Parte Todas
    .\animar-emanuelly.ps1 -Acao Preparar -Parte Todas
    .\animar-emanuelly.ps1 -Acao Renderizar -Parte Todas
    .\animar-emanuelly.ps1 -Acao Abrir -Parte Todas

Sem orçamento, o gerador de imagens não faz chamadas pagas.
GerarImagens envia a referência ao Codex Proxy, que pode encaminhá-la
ao serviço de imagens. O modelo é sempre gpt-image-2; não existe fallback
para 1.5. Respostas pagas são preservadas antes do QA.

A narração e as músicas PT-BR existentes são reutilizadas. O render
final-camadas.mp4 fica separado de final.mp4, preservando o vídeo antigo
e as versões anteriores em histórico. Não há upload ao YouTube.

**Limitação:** camadas e sprites movimentados independentemente
não substituem rigging completo, lipsync ou revisão visual das cenas.
A conferência final deve ser feita no vídeo, para garantir que Manu
realmente segura o mesmo ovo e abraça o mesmo Fofinho.
