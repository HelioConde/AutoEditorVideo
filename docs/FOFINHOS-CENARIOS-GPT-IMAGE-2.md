# Fofinhos — recriar o mesmo jardim e quarto em quatro ângulos (GPT Image 2)

Este gerador produz **nove recursos canônicos** para os quatro Shorts da
origem de Fofinho: quatro visões **do mesmo jardim**, quatro visões
**do mesmo quarto** e um **ovo azul isolado**, sempre com a identidade da série.

## Estratégia de consistência visual

| Arquivo | Referência da edição | Composição |
|---|---|---|
| jardim-01.png | emanuelly-solo.png (estilo, não elenco) | Plano geral do jardim, base |
| quarto-01.png | jardim-01.png | Plano geral do quarto, estilo correspondente |
| ovo-azul.png | jardim-01.png | Ovo azul isolado, transparência real |
| jardim-02.png | jardim-01.png | Vista deslocada à esquerda |
| jardim-03.png | jardim-01.png | Vista deslocada à direita |
| jardim-04.png | jardim-01.png | Aproximação baixa junto ao caminho |
| quarto-02.png | quarto-01.png | Vista lateral esquerda do mesmo quarto |
| quarto-03.png | quarto-01.png | Vista lateral direita do mesmo quarto |
| quarto-04.png | quarto-01.png | Aproximação junto à cama |

**Importante:** os três ângulos alternativos de cada cenário são edições
do MESMO quadro-mestre, não gerações independentes de texto. Prompts bloqueiam
mudanças de árvores, caminhos, cerca, portão, móveis, janela e decoração.
Isso aumenta a consistência, mas **não garante geometria 3D idêntica**:
olhe todas as imagens antes de usá-las em um vídeo.

Os cenários **não contêm Emanuelly, ovo ou Fofinho**. Personagens e ovo são
sobreposições independentes no Remotion. Para a noite, a iluminação é aplicada
pelo renderizador, não incorporada ao PNG do quarto.

## Windows: planejar e gerar

Na pasta do projeto:

    cd "C:\Users\helio\Documents\arquivo-otaku-github"
    git pull --ff-only origin main

Confirmar previamente as imagens e os custos, sem enviar nada:

    .\gerar-cenarios-fofinhos.ps1 -Acao Planejar

### Etapa 1: três bases

    .\gerar-cenarios-fofinhos.ps1 -Acao GerarBases -MaxChamadas 3
    .\gerar-cenarios-fofinhos.ps1 -Acao Abrir

Examinar jardim-01.png, quarto-01.png e ovo-azul.png.
**Não executar a etapa seguinte até aprovar visualmente as três bases.**
Uma nova chamada à API pode ter custo. Se estiver insatisfeito, é possível
refazer o lote de bases com backup e até três novas chamadas:

    .\gerar-cenarios-fofinhos.ps1 -Acao GerarBases -MaxChamadas 3 -Refazer

### Etapa 2: seis ângulos

Somente depois de visualizar as três bases e confirmar que estão boas:

    .\gerar-cenarios-fofinhos.ps1 -Acao GerarAngulos -BasesAprovadas -MaxChamadas 6

Abrir as nove imagens e comparar os mesmos detalhes físicos em todos os
ângulos:

    .\gerar-cenarios-fofinhos.ps1 -Acao Abrir
    .\gerar-cenarios-fofinhos.ps1 -Acao Verificar
    .\animar-emanuelly.ps1 -Acao Planejar -Parte Todas

As imagens são salvas automaticamente em:

    assets\gerados\kids-emanuelly\cenarios-oficiais\

O gerador registra os recursos oficiais usando o sistema de instalação
existente. Os quatro Shorts usam esses mesmos arquivos, sem importações
manuais duplicadas. **Teto para gerar os nove do zero: até 9 chamadas
gpt-image-2**, sendo 3 + 6. Não se trata de estimativa de custo em reais.

## Segurança, dados locais e recuperação

- Usa exclusivamente gpt-image-2 no Codex Proxy configurado no projeto.
- A referência privada emanuelly-solo.png é enviada para criar somente
  jardim-01.png; as demais gerações usam imagens de cenários.
- O Codex Proxy pode transmitir essa imagem privada ao provedor configurado.
  A chamada é feita apenas quando o criador executa GerarBases/GerarAngulos.
- Todos os arquivos de referência, brutos, imagens, metadados, versões antigas
  e resultados ficam no Windows e são ignorados pelo Git.
- Resposta paga é armazenada em cenarios-oficiais/brutos ANTES da validação.
- A integridade de cada recurso e o SHA-256 da imagem-base são registrados.
  Quando a base muda, os derivados gerados anteriormente são sinalizados
  como desatualizados, para regeneração explícita com -Refazer.
- Arquivos previamente válidos são reutilizados sem cobrança de nova chamada.
- Nenhuma publicação no YouTube, nenhuma criação automática de vídeo e
  nenhuma alteração das poses existentes.
- O ovo deve ter alfa verdadeiro; cenários são opacos, 1024×1536.

### Testes sem IA

    python -m pytest -q tests/test_gerar_cenarios_fofinhos_gpt_image_2.py

O teste simula respostas PNG e verifica orçamento prévio, fontes corretas,
transparência, armazenamento, cache e invalidação. Nem os testes nem o GitHub
Actions usam suas fotos privadas.
