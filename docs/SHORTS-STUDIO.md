# Shorts Studio — painel local do Arquivo Otaku

O `Shorts Studio` é uma interface no navegador que roda **somente no seu Windows** (127.0.0.1 com porta aleatória). Não é um site público nem um serviço GitHub Pages. Usa Python da `.venv` e bibliotecas padrão para o servidor; as dependências de imagem continuam as mesmas.

## Abrir

```powershell
cd C:\Users\helio\Documents\arquivo-otaku-github
git pull origin main
.\abrir-shorts-studio.ps1
```

Deixe a janela de PowerShell aberta: ela mantém o servidor local. O navegador abrirá com botões de **Verificar cache**, **Planejar**, **Validar**, **Recriar sem IA**, **Reparar fundo**, **Gerar com IA** e **Renderizar**. Todos os comandos exibem logs no painel; não há publicação automática no YouTube.

## Quando diz "3 imagens pendentes" mas foram geradas antes

Isso **não é falta de créditos**. O cache é identificado pelo hash do **modelo + prompt**. Se o storyboard foi refeito ou o modelo mudou, o gerador procura uma pasta de hash diferente. A partir desta versão, a primeira produção preserva um snapshot de storyboard em:

`assets/gerados/shorts-animados/<episodio>/storyboard-producao.json`

Ele deixa de replanejar automaticamente a cada execução, mantendo os mesmos hashes. Para gerar novo storyboard deliberadamente, use `-Replanejar` (o anterior recebe backup). Se o problema já ocorreu antes da atualização, use **Verificar cache** para listar as versões antigas e decidir qual projeto usar. Nunca reutilizamos um fundo/foreground de prompt diferente de maneira automática.

```powershell
.\gerar-shorts-master.ps1 -Id 003-death-note-xadrez -Cena 6 -DiagnosticarCache -MaxChamadas 0
```


### Solução para a cena 06 depois da correção no Photoshop

A cena 06 do episódio `003-death-note-xadrez`, gerada com `gpt-image-1.5`,
tem a versão revisada e preservada em `06-594007f1c10bb8`. O storyboard
fixado posteriormente passou a procurar outro hash, embora o cache original
estivesse salvo no Windows.

O arquivo versionado `configs/scene-cache-pins.json` **seleciona
explicitamente** essa pasta de cache para essa única combinação
episódio + modelo + cena. Isso não copia, apaga, renomeia nem sincroniza
imagens para o GitHub. O vínculo também preserva o ajuste `y=-211`
definido em `configs/foreground-placements.json`.

Depois de `git pull origin main`, execute:

```powershell
.\gerar-shorts-master.ps1 -Id 003-death-note-xadrez -Cena 6 -Modelo gpt-image-1.5 -DiagnosticarCache -MaxChamadas 0
.\gerar-shorts-master.ps1 -Id 003-death-note-xadrez -Cena 6 -Modelo gpt-image-1.5 -MaxChamadas 0 -Offline
```

O diagnóstico deve mostrar `[SELECAO EXPLICITA]` e a execução deve
mostrar `[CACHE FIXADO] 06: 06-594007f1c10bb8`. Se essa pasta foi
movida ou não está completa, o programa **para antes de solicitar novas
imagens** e informa os arquivos ausentes. Confirme que o
`qa.json` da pasta corresponde ao episódio e à cena, sem editar nem
transferir indiscriminadamente imagens de versões diferentes.

Para outra cena ou modelo, não será aplicado esse pin. Para selecionar
outra versão intencionalmente, revise `configs/scene-cache-pins.json`;
nunca use o mesmo pin para modelos diferentes sem conferir a origem.
O renderizador Remotion agora lê o mesmo storyboard fixado que o
gerador, evitando divergência entre os passos.

## Conexão do Codex Proxy ≠ limite de chamadas

```powershell
.\gerar-shorts-master.ps1 -StatusCodex
```

A consulta gratuita (sem imagem) distingue: Docker/proxy offline, chave local ausente, falha na autenticação, conta conectada sem elegibilidade e proxy conectado com conta elegível. A disponibilidade muda conforme o servidor e a conta. **Não há garantia de login permanente nem de acesso ilimitado**. `-MaxChamadas` limita **quantas novas imagens a execução pode solicitar**; é uma proteção de custo, não a cota do Codex e não deve ser substituída por um teste de login.

O Studio verifica a conexão periodicamente enquanto está aberto. Use **Iniciar proxy** para ligar uma instalação existente do Docker Compose (sem rebuild), caso confie no serviço comunitário, e **Fazer login** para iniciar autenticação com autorização manual. Nunca copie chaves ou códigos de login para o GitHub.

### Manter o serviço disponível

No Docker Desktop, configure o aplicativo para iniciar junto do Windows. Caso a instalação do serviço tenha uma política de reinício compatível (`restart: unless-stopped`), ela pode recuperar o processo após reinicializações do Docker. Essas configurações não preservam uma autorização expirada: nesse caso, é necessário fazer login de novo. O Studio não altera `compose.yaml`, não reloga automaticamente e não troca de conta para contornar limites.

## Segurança e diagnósticos

- O servidor só escuta `127.0.0.1`, valida Host, origem, token local temporário e comandos permitidos.
- Operações com IA exigem clique explícito e confirmação no navegador. `-MaxChamadas 0` impede novas chamadas.
- O painel mostra logs localmente sem salvar tokens. Os arquivos `.env` e resultados de imagens continuam no seu PC.
- **Reparar fundo** limita-se a uma cena por vez e preserva o backup do background pago.
- Se aparecer erro no terminal, confira o log e use **Verificar cache** antes de autorizar nova geração.


## Windows: `[Errno 22] Invalid argument: background-mask.png`

Isso pode acontecer quando a máscara existente está aberta/bloqueada por um
visualizador ou editor no Windows. A composição 2.5D com
`background-raw.png` já em cache **não precisa gravar a máscara outra vez**.

A partir desta correção, o motor calcula a máscara somente em memória para
o QA e para conferir fundos limpos, sem abrir, sobrescrever nem apagar
`background-mask.png` no fluxo offline com fundo já gerado. Ele continua
preservando as camadas raw e o deslocamento da cena 06.

```powershell
git pull origin main
.\gerar-shorts-master.ps1 -Id 003-death-note-xadrez -Cena 6 -Modelo gpt-image-1.5 -MaxChamadas 0 -Offline
```

Procure `[MASCARA] 06: calculada em memoria`, `[POSICIONAMENTO]` e
`[FUNDO]` no log. Isso não gera imagens com IA. Se você precisar
**regenerar** o background usando `-RepararFundo`, a máscara ainda será
escrita no disco, pois a API de edição a utiliza; feche antes qualquer
aplicativo que a esteja segurando e reexecute. Se a escrita falhar,
nenhuma chamada de edição é enviada e os arquivos raw continuam preservados.

