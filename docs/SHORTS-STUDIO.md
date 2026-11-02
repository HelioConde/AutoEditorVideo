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
