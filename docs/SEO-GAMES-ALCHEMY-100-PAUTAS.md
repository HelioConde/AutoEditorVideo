# SEO aplicado às 100 pautas Gamer e IA — 05/11/2026

**Status:** metadados propostos para futuras produções; nenhum vídeo gerado, publicado, reeditado no YouTube ou reservado por estes arquivos.

## Fontes dos 100 registros

| Canal | Arquivo da lista com SEO | Quantidade | Intercalação |
|---|---|---:|---|
| Hélio Conde (Gamer) | [`conteudos/helio-conde-games-grade-50-seo-v1.json`](../conteudos/helio-conde-games-grade-50-seo-v1.json) | 50 | Você Sabia? (17), Você Lembra? (17), Jogos do Momento (16) |
| IA (marca planejada Alchemy Lab) | [`conteudos/alchemy-lab-grade-50-v1.json`](../conteudos/alchemy-lab-grade-50-v1.json) | 50 | Você Sabia? (17), Testei por Você! (17), IA na Prática (16) |

Ambos seguem a política registrada em [`config/seo-metadata-policy-v1.json`](../config/seo-metadata-policy-v1.json) e as orientações de [`docs/SEO-VIDIQ-METADADOS-5-CANAIS.md`](SEO-VIDIQ-METADADOS-5-CANAIS.md).

Cada registro de `episodes[]` contém:
- `title_proposed`: o título original da pauta, preservado da lista.
- `seo.title_draft`: título sugerido para SEO (sem substituir o original).
- `seo.primary_keyword`: palavra-chave principal única, alinhada ao vídeo.
- `seo.description_draft`: descrição contextual individual, com chamada para ação adequada ao quadro.
- `seo.hashtags`: três hashtags focadas no tema, incluídas também no fim da descrição.
- `seo.tags`: nove tags para o campo interno do YouTube Studio; não colar como parágrafo de hashtags.
- `seo.metadata_status`: **draft_pending_factual_and_video_review**. Sem revisão, não publicar.

## Qualidade validada antes do commit

- Ambos os catálogos contêm **50 posições válidas**, totalizando 100.
- A alternância 1–2–3 dos quadros foi preservada nos 50 episódios de cada canal.
- Todos os 100 registros têm título, palavra-chave, descrição, hashtags e tags.
- Não há descrições duplicadas integralmente em cada catálogo nem tags repetidas dentro de um vídeo.
- Títulos com no máximo 100 caracteres; tags com até 500 caracteres; descrições com até 5.000; todos com 8–15 tags e 2–4 hashtags.
- Nenhuma entrada autoriza publicação. Os catálogos não criam OAuth, workflows, uploads ou reservas.

## Diferenças de identidade e cuidados

**Gamer** permanece **Hélio Conde** (`UCg77gYc1_wkHuL07XPtKcow`), sem renomear para Conde Games. Alegações de partidas, descobertas, desafios e testes exigem gameplay próprio/licenciado; nomes de lançamentos, eventos e promoções devem ser verificados em fontes oficiais perto da publicação.

**IA** permanece cadastrada sob o nome observado **Alchemy Flames** (`UCCTYFE5Cmz2aYZ37cJQ-wcg`); **Alchemy Lab é a marca planejada**, ainda não tratada como renomeada. Versões de modelos e funcionalidades não confirmadas devem ser checadas. Para vídeos “Testei por Você!”, o experimento precisa existir, com evidências reais, antes de utilizar título e descrição definitivos.

## Próxima etapa (não executada)

Antes de gerar qualquer roteiro, comando de produção, imagem, vídeo ou agendamento:

1. Pesquisar palavras-chave atuais com o vidIQ caso haja créditos; nesta rodada não houve nova pesquisa porque o saldo foi reportado como **zero**, com renovação em 03/12/2026. As tags propostas não têm pontuação de pesquisa afirmada.
2. Confirmar fatos, nome da ferramenta/jogo, versão, licenças, fontes e resultado dos testes.
3. Rever `seo.description_draft` como **rascunho contextual**, transformando referências ao planejamento e testes em uma descrição fiel ao vídeo efetivamente finalizado. Confirmar o mesmo para `seo.title_draft`.
4. Fazer a **reserva do canal + ID de episódio na main** em `conteudos/otaku-production-reservations.json` antes de qualquer script/comando/asset/MP4 conforme `AGENTS.md`.
5. Preservar OAuth separado, verificação exata de Channel ID, fluxo de QA e privacidade inicial privada; não habilitar automaticamente uploader de Gamer ou IA.

O score do vidIQ não é uma nota do algoritmo do YouTube. Priorizar relevância e a experiência do espectador em vez de preencher limite de tags ou repetir a descrição.
