<div align="center">
<h1>🎬 Arquivo Otaku</h1>
<p><strong>Produção de Shorts sobre anime: ideias → roteiro → imagens IA → vídeo → miniaturas → YouTube</strong></p>
<p>Projeto local e gratuito para instalar; as APIs podem ter cotas, indisponibilidade ou custos conforme a conta.</p>
</div>

> **Substitui o AutoEditor Studio** neste repositório a partir de v0.8. O editor
> anterior permanece integralmente na branch
> [`backup/autoeditor-studio-2026-11-01`](../../tree/backup/autoeditor-studio-2026-11-01).

## Painel Shorts Studio (Windows)

Para controlar o gerador de cenas por botões, acompanhar logs e verificar o
Codex Proxy sem gerar imagens:

```powershell
.\abrir-shorts-studio.ps1
```

O painel roda apenas em `127.0.0.1` no seu computador. Ele identifica quando
o storyboard mudou de hash e lista caches antigos sem confundir isso com
créditos ou desconexão. Consulte [o guia Shorts Studio](docs/SHORTS-STUDIO.md).

## O que este projeto faz

- **Radar de pautas**: 14 temas de anime e fila editorial diversa, com ganchos revisáveis;
- **Roteiro / QA editorial**: checa tese, promessas e variedade visual;
- **Imagens 2D**: gera cenas pelo `chatgpt-codex-proxy` local, se a conta estiver elegível;
- **Alternativa sem IA**: reutiliza imagens existentes, ajusta iluminação e enquadramentos;
- **Edição vertical**: MoneyPrinterTurbo e FFmpeg, legendas e voz em PT-BR;
- **Miniaturas**: YouTube 16:9 e Shorts/TikTok 9:16;
- **YouTube**: título e descrição, OAuth oficial, registro para evitar upload duplicado;
- **Testes**: Python com pytest; não acessam contas pessoais nem geram vídeos.

**Importante:** isto é um programa de **Windows/PowerShell**, não um serviço de
geração em GitHub Pages. A página do repositório apenas apresenta as instruções.
O projeto não envia vídeos ao TikTok automaticamente.

## Primeiros passos (Windows)

```powershell
git clone https://github.com/HelioConde/AutoEditorVideo.git
cd AutoEditorVideo

# Python 3.11 + MoneyPrinterTurbo via uv
winget install --id=astral-sh.uv -e
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\instalar-windows.ps1

# Radar e planejamento, sem IA e sem upload
.\radar-conteudo.ps1
.\radar-conteudo.ps1 -Id hxh-killua
.\planejar-episodio.ps1

# Testes do plano
.\gerar-video-codex.ps1 -SomenteConfigurar
```

Para novas imagens com o Codex Proxy, inicie o Docker e siga
[`GUIA-CODEX-PROXY.md`](GUIA-CODEX-PROXY.md). Ele é um serviço de terceiros
que usa interfaces não oficiais, sujeito a mudanças, permissões e cotas.

```powershell
# Com conta elegível, gerar um Short com novas imagens
.\gerar-video-codex.ps1 -Modelo gpt-image-1.5

# Sem conta elegível, reciclar imagens locais
.\gerar-video-codex.ps1 -ReutilizarImagens
```

**Atenção:** o script de vídeo atual é um piloto do episódio Death Note; o radar
não aciona automaticamente toda a produção de um novo anime. Para criar um
episódio novo, é preciso preparar e revisar o JSON em `conteudos/`.

## YouTube — publicar somente após revisão

Crie as credenciais OAuth oficiais do tipo **Aplicativo para computador**,
salvando-as somente na pasta local `.secrets/`. Instruções em
[`GUIA-PUBLICAR-YOUTUBE.md`](GUIA-PUBLICAR-YOUTUBE.md).

```powershell
# Checagem sem upload
.\publicar-youtube.ps1 -Etapa diagnostico
# Criar capas e metadados, sem upload
.\publicar-youtube.ps1 -Etapa preparar
# Publicar um vídeo preparado (privado, para revisão)
.\publicar-youtube.ps1 -Etapa enviar -Privacidade private
```

O código atual aceita `-Privacidade public` explicitamente. Antes de publicar,
verifique copyright, narração, erros no roteiro, legendas e miniatura.

**Privacidade:** não execute `-Etapa tudo` sem conferir a opção `-Privacidade`;
alguns scripts herdados podem sugerir publicação pública como padrão.

## Garantia de segurança

Não publique `.secrets/`, `.env`, `youtube-token.json`, imagens de personagem
ou vídeos em GitHub. Há regras em `.gitignore` para barrar esses arquivos,
mas revise também `git status` antes de qualquer push.

## Documentação

- [Evolução v0.8](LEIA-ME-v0.8.md)
- [Referências analisadas](docs/BENCHMARK-V08.md)
- [Instalação do Codex Proxy](GUIA-CODEX-PROXY.md)
- [YouTube OAuth](GUIA-PUBLICAR-YOUTUBE.md)
- [Direitos e revisão](docs/DIREITOS-E-REVISAO.md)

## Testar

```powershell
.\.venv\Scripts\python.exe -m pip install pytest
.\.venv\Scripts\python.exe -m pytest -q tests
```

> A execução local de imagens IA depende do proxy e de acesso válido.
> O GitHub Actions valida apenas lógica local, sem credenciais e sem cobranças.

Desenvolvido por [Hélio Conde](https://github.com/HelioConde).

## Planejador editorial sincronizado v0.9

O modulo arquivo_otaku.pipeline aceita episodios independentes e legendas SRT. E apenas um planejador: a exportacao final pelo MoneyPrinterTurbo ainda precisa seguir o fluxo local.

```powershell
python -m arquivo_otaku.pipeline --episodio arquivo_otaku/episodios/death-note.json --srt caminho/legendas.srt
```

## Segundo Short — Light investigando Kira (v0.9.2)

O episodio 002 esta pronto para gerar no Windows, mas exige Codex Proxy com conta elegivel. Primeiro valide sem gastar cota:

```powershell
.\segundo-short-death-note.ps1 -Etapa plano
```

Para gerar as sete imagens novas, o video e as capas correspondentes:

```powershell
.\segundo-short-death-note.ps1 -Etapa criar -Modelo gpt-image-1.5
```

Para preparar capas/metadados novamente, sem gerar novas imagens:

```powershell
.\segundo-short-death-note.ps1 -Etapa preparar
```

Depois de assistir e revisar, enviar como privado:

```powershell
.\segundo-short-death-note.ps1 -Etapa publicar
```

Para publicar como publico, apenas apos revisao:

```powershell
.\segundo-short-death-note.ps1 -Etapa publicar -Privacidade public -ConfirmarPublico
```

A nova saida e `assets/gerados/arquivo-otaku-002-death-note-memoria-codex.mp4`. O video 001 permanece intacto. Consulte [30 pautas de Death Note](docs/DEATH-NOTE-PAUTAS-v1.md).

## Hotfix v0.9.3 — PermissionError ao salvar recortes

Se o segundo Short gerou as 7 imagens e falhou no caminho `otaku-v07-*.partial.jpg`, os arquivos de IA **ja estao em cache**. Atualize o codigo, depois execute novamente:

```powershell
.\segundo-short-death-note.ps1 -Etapa criar -Modelo gpt-image-1.5
```

A proxima execucao devera exibir `0 cenas exigem IA` e `[CACHE]` nas 7 cenas. O editor agora usa temporarios aleatorios e salva recortes em pastas proprias de cada episodio. Se houver novo `PermissionError`, confira as permissoes de escrita/Windows Defender na pasta `.mpt-runtime\storage\local_videos`. Nao apague imagens originais nem o cache.

## Lote de 25 Shorts — planejamento e renderizacao local (v0.9.3)

Foi adicionado um **gerenciador de fila** com 25 pautas diferentes de Death Note.
Os roteiros ainda precisam ser preparados e revisados antes da renderizacao;
o sistema recusa roteiros nao aprovados e **nao publica em massa**.

```powershell
.\lote-25.ps1 -Acao status
.\lote-25.ps1 -Acao renderizar
# Somente depois de aprovar episodios em dados/lote-25-pautas.json:
.\lote-25.ps1 -Acao renderizar -ConfirmarRender
```

Leia [o guia do lote](docs/LOTE-25.md).

## Motor de animação Remotion (experimental)

Foi integrado um segundo renderizador que anima personagem, objetos e câmera com movimentos por tipo de cena, reutilizando voz e legendas em cache. Ele **não faz upload**, não altera vídeos anteriores e bloqueia PNG opaco ou com verde residual.

Documentação e instalação: [motion-remotion/README.md](motion-remotion/README.md). Análise dos motores GitHub: [docs/ESCOLHA-DO-MOTOR-DE-ANIMACAO.md](docs/ESCOLHA-DO-MOTOR-DE-ANIMACAO.md).

## Cenas por acontecimentos do roteiro (sem quantidade fixa)

O número de imagens é decidido pelas mudanças narrativas, não por um valor padrão. O planejador local propõe cortes e permite `blocos_visuais` escritos pelo roteirista. Para planejar o xadrez sem gastar IA:

```powershell
.\planejar-cenas.ps1 -Id 003-death-note-xadrez
```

O JSON gerado é uma **proposta visual para revisão**; ainda não constitui um vídeo final nem aciona automaticamente o gerador de imagens-mãe. Veja [docs/CENAS-DINAMICAS.md](docs/CENAS-DINAMICAS.md).

## Fluxo integrado: imagens-mãe multicenas por roteiro (v1.4)

O clone inclui geração de storyboards com quantidade variável de enquadramentos, extração com alpha nativo via image edits, cenário reconstruído da mesma imagem, narração, legendas e render Remotion. Nenhuma publicação automática.

```powershell
.\gerar-shorts-master.ps1 -Id 003-death-note-xadrez -SomentePlanejar
```

Guia completo: [docs/MULTICENAS-DINAMICAS.md](docs/MULTICENAS-DINAMICAS.md).


## TikTok — upload oficial dos cinco Shorts (Content Posting API)

O projeto agora oferece publicação no TikTok por meio da **API oficial**, reutilizando os MP4s já renderizados. O modo padrão envia **rascunhos** para finalizar pelo aplicativo TikTok; a publicação direta só funciona com o escopo `video.publish` aprovado e está sujeita à auditoria e às opções de privacidade da conta.

```powershell
# Primeiro leia docs/PUBLICAR-TIKTOK.md e configure seu aplicativo em developers.tiktok.com
.\publicar-tiktok.ps1 -Acao diagnostico
.\publicar-tiktok.ps1 -Acao preparar -Limite 5
.\publicar-tiktok.ps1 -Acao conectar -Modo rascunho
.\publicar-tiktok.ps1 -Acao enviar -Modo rascunho -Limite 1 -ConfirmarEnvio
.\publicar-tiktok.ps1 -Acao status -Modo rascunho
```

Guia: [Publicar no TikTok](docs/PUBLICAR-TIKTOK.md). Tokens locais ficam em `.secrets/` e não vão ao GitHub. Os envios possuem histórico por hash para evitar duplicatas; não há publicação automática sem consentimento explícito.

## Canal internacional — Otaku Archives (EN)

O pipeline pode adaptar os cinco Shorts existentes para inglês sem gerar novas imagens.
Produz nova voz `en-US`, legendas sincronizadas, capa inglesa e MP4 separado em
`assets/gerados/shorts-animados/<ID>/en-US/`. Nenhum upload ocorre durante a geração.

```powershell
.\gerar-shorts-en.ps1 -Acao planejar
.\gerar-shorts-en.ps1 -Acao voz
.\gerar-shorts-en.ps1 -Acao renderizar
```

O novo canal YouTube precisa ser criado pelo usuário no YouTube. O publicador
`publicar-shorts-en.ps1` exige autenticação OAuth **separada**, com conferência
do Channel ID antes de qualquer upload para não misturar os dois canais.

Guia completo: [Criar e publicar no segundo canal em inglês](docs/CANAL-INGLES.md).


## REGRA MESTRA — Shorts de no máximo 60 segundos

**Todos os Shorts do Arquivo Otaku e Otaku Archives (YouTube PT/EN e TikTok) precisam durar 60,000 segundos ou menos no arquivo MP4 final.** Inclui abertura, narrativa, final de suspense, CTA de inscrição e a margem de renderização. A faixa recomendada para escrever e editar é **55–59 segundos**.

O editor bloqueia automaticamente a montagem quando a narração mais a margem ultrapassa 60 segundos e recusa publicar qualquer MP4 cuja duração real exceda esse teto (checagem via FFprobe). Não acelere a voz nem corte o gancho/CTA para contornar a regra. **Reescreva o roteiro, regrave e renderize novamente**.

Implementação: [scripts/shorts_duration.py](scripts/shorts_duration.py) · Testes: [tests/test_shorts_duration.py](tests/test_shorts_duration.py) · Política para agentes: [AGENTS.md](AGENTS.md).


## Produzir e publicar um Short completo em um comando

Use o novo modo de geração, narração, cenas com IA, animação, capa, descrição e upload YouTube. O processo retoma cenas em cache após falhas recuperáveis, respeita limite total de **60 segundos** e nunca publica um vídeo incompleto.

```powershell
cd "C:\Users\helio\Documents\arquivo-otaku-github"
git pull --ff-only origin main
.\criar-publicar-short.ps1 -Id 101-death-note-ep01 -Publicar -Privacidade public
```

Outros episódios: `102-death-note-ep02` e `103-death-note-ep03`.
Para gerar sem publicar, basta omitir `-Publicar`. Publicação direta exige credenciais YouTube OAuth já configuradas; o upload registra hash/ID e a capa correta é preservada localmente mesmo se a API do YouTube bloquear a miniatura do Short.

Guia: [Comando único para Shorts](docs/COMANDO-UNICO-SHORTS.md).

