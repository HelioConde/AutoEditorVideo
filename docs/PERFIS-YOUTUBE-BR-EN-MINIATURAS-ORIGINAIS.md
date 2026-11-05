# Perfis de upload para Otaku Multicena (BR) e Otaku Reframe (EN)

**Regra permanente solicitada em 05/11/2026:** todo Short usa **sempre a
miniatura original gerada pelo AutoEditorVideo para aquele episódio e canal**.

Os perfis estão versionados em
`config/youtube-upload-profiles.json` e executados por
`scripts/youtube_upload_profiles.py` nos uploads novos. O gerador
`scripts/otaku_dual_5011_cloud.py` empacota as capas dos canais de forma
independente e registra seu **SHA-256** no `review-summary.json`. O upload
cloud usa `verified_generated_cover(...)` e rejeita ausência, canal errado,
arquivo não JPEG 9:16, origem que não seja AutoEditorVideo ou hash divergente.

Nenhum código tem permissão para substituir a miniatura por:
- quadro aleatório ou screenshot do MP4;
- sugestão automática do YouTube ou imagem gerada pelo Studio;
- capa BR utilizada no EN (ou vice-versa);
- arte IA refeita na hora da publicação;
- capa de outro vídeo.

Se a capa não passar, **bloquear o upload antes de `videos.insert`**.
Se o YouTube aceitar o MP4 mas recusar a capa por cota/permissão/processamento,
preservar o recibo, deixar o vídeo privado e marcar a miniatura pendente.
Nunca reenviar MP4. Só considerar o pacote pronto para liberação pública
quando a API confirmar a capa. O usuário pode conferir o resultado no Studio.

## Configurações automáticas via API (novos vídeos)

| Campo | Otaku Multicena | Otaku Reframe |
|---|---|---|
| Canal OAuth | `UCXGYTuBYn-0Ziqin5ajKhOw` | `UCBoNbQjaMYdpJqPLRZAFkvQ` |
| Idioma dos metadados | `pt-BR` | `en-US` |
| Categoria | Filme e animação (`1`) | Filme e animação (`1`) |
| Privacidade inicial | `private` | `private` |
| Destinado a crianças | Não | Não |
| Licença | Padrão do YouTube (`youtube`) | Padrão do YouTube (`youtube`) |
| Incorporação | Permitida | Permitida |
| Estatísticas públicas | Permitidas | Permitidas |
| Notificar inscritos | Sim (sujeito às regras do YouTube) | Sim (sujeito às regras do YouTube) |
| Título | Roteiro BR específico | Roteiro EN específico |
| Descrição | Comentário, CTA, avisos e hashtags BR | Comentário, CTA, avisos e hashtags EN |
| Tags | Relevantes para o anime, até 500 caracteres | Relevantes para o anime, até 500 caracteres |
| Miniatura | JPG gerado e assinado BR | JPG gerado e assinado EN |

O perfil não copia tags de `Death Note` para `Gachiakuta`, `Aoashi`,
`Overgeared` ou outro anime. Tags sobre filmes completos gratuitos, idioma
hindi ou marcas desconexas são rejeitadas quando não são tópicos do vídeo.

`containsSyntheticMedia` é incluído na requisição de upload **somente após
uma avaliação explícita por vídeo**, usando verdadeiro/falso no metadado.
Não é seguro inferir que qualquer anime ilustrado por IA seja realista e
também não é seguro omitir declaração quando for exigida pela política.

## Configurações do YouTube Studio que precisam de revisão

As seguintes preferências foram documentadas, mas não são impostas pela API
do upload atual: comentários ativados; moderação **nenhuma** no BR e
**básica** no EN; quem pode comentar (todos); capítulos, lugares e
conceitos automáticos permitidos; remixes de áudio e vídeo; restrição
etária somente quando necessária; promoções pagas somente quando houver;
legendas/idioma falado; certificação de legendas nenhuma quando não exigida;
exibir curtidas e publicar no feed conforme opções do canal. A API atual
não permite confirmar todos esses controles com um único
`videos.insert`; verificá-los no Studio antes de publicar.

**Não** modificar vídeos já públicos, privados ou agendados automaticamente
para impor perfis novos. Os uploads existentes permanecem inalterados.

## Miniaturas Shorts em novembro/2026

A documentação oficial do YouTube Data API foi atualizada em **03/11/2026**
para permitir `thumbnails.set` em Shorts após `processingDetails.processingStatus=succeeded`.
A miniatura pode levar tempo para se refletir na interface e a visualização
nos diversos feeds fica a cargo do YouTube.

Fontes:
- https://developers.google.com/youtube/data/reference/rest/v3/thumbnails/set
- https://developers.google.com/youtube/data/reference/rest/v3/videos/insert
- https://support.google.com/youtube/answer/72431?hl=pt-BR

## Verificação local offline ou no GitHub

```bash
python -m pytest -q tests/test_youtube_upload_profiles.py tests/test_youtube_short_thumbnails.py tests/test_cloud_youtube_private_5011.py
```

Esses testes usam somente miniaturas sintéticas temporárias. Nenhuma imagem
é gerada por IA, nenhum vídeo é reenviado e nenhum OAuth é acessado em PRs.

## Identificadores internos e descrições

A chave interna de deduplicação da geração **não pertence à descrição**.
Versões antigas do uploader adicionavam linhas como
`AUTOEDITORVIDEO-5011-en-fdc3d3a734833529`; essa prática foi removida.

- O `videos.insert` publica somente descrição editorial, hashtags, CTA e
  avisos relevantes. A chave de deduplicação fica no recibo do upload, fora
  do YouTube.
- O marcador antigo continua sendo procurado no histórico do canal
  **apenas para detectar uploads já existentes**. Comparação do título
  continua como proteção extra. Nenhum MP4 deve ser reenviado.
- O sanitizador compartilhado remove marcadores legados válidos
  que porventura apareçam em manifestos; marcadores malformados bloqueiam o
  upload em vez de ir parar na descrição.
- Essa regra se aplica aos uploaders BR e EN cloud e locais.

**Descrições de vídeos já enviados** não são alteradas automaticamente pelo
merge do PR. Para retirar o marcador de um Short antigo sem mexer em
privacidade e agendamento, abra o YouTube Studio, edite somente a última
linha com `AUTOEDITORVIDEO-...` na descrição e salve. A alternativa via API
`videos.update(part=snippet)` requer OAuth que inclua `youtube.force-ssl`
e exige reenviar os demais campos mutáveis do snippet, sob risco de apagar
tags ou idioma existentes se omitidos — não é a mesma autorização básica
de upload.

Referência da API:
https://developers.google.com/youtube/data/reference/rest/v3/videos/update

