# Design system — AutoEditor Studio

## Direção visual
**Estúdio criativo profissional, sem complexidade visual.** Base carvão, acento lima e ilustrações geométricas construídas com CSS. Evitar gráficos fictícios, contadores estáticos, banners decorativos que pareçam botões e telas sem próximo passo.

## Tokens
| Token | Valor | Uso |
|---|---|---|
| `--bg` | `#101214` | Background base |
| `--sidebar` | `#131618` | Navegação |
| `--surface` | `#191d20` | Superfícies |
| `--surface2` | `#202529` | Superfícies elevadas |
| `--stroke` | `#313638` | Delimitadores |
| `--accent` | `#d5f579` | Ação principal, destaque e foco |
| `--text` | `#f0f0eb` | Conteúdo primário |
| `--subtle` | `#a3acaa` | Descrições |
| `--radius` | `16px` | Cards |

Tipografia: Plus Jakarta Sans em títulos; DM Sans em interface/texto; fontes substitutas `system-ui` se indisponíveis. H1 fluido, hierarquia H1 > H2 > H3. Espaçamentos em múltiplos de 4/8 px (8, 12, 16, 24, 32, 48), com ajustes ópticos pontuais. Bordas discretas, sombras curtas e radii aninhados. Evitar animações contínuas não essenciais.

## Componentes principais
- `Sidebar`/navegação: `button` para trocar estado, marcação `aria-current`.
- `btn-primary`: ação principal lima, texto escuro. `btn-outline`: secundária.
- `Panel` e `StatCard`: dados reais, sem promessas de recursos não implementados.
- Modal de projeto: `role=dialog`, foco inicial, loop de Tab, retorno de foco, Escape.
- Upload: `input type=file` com label, feedback de progresso/erro e limites visíveis.
- Campos de recorte com label/valor, opção de formato em radio nativo.

## Acessibilidade e responsividade
- Idioma `pt-BR`, skip link, landmarks semânticos, labels, feedback `aria-live`, foco `:focus-visible`.
- Botões e inputs com alvos móveis de 44px quando interativos; mínimo 16px em campos móveis.
- Sem rolagem horizontal em larguras 320, 375, 768, 1280, 1920px.
- Mobile: menu sobreposto com botão de fechar; editor passa de duas colunas para uma.
- `prefers-reduced-motion` desabilita efeitos não essenciais.
- Erros acionáveis; recurso futuro explicitamente marcado `Em breve` e nunca representado como pronto.

## QA visual e Image-to-Code
Sem screenshots fornecidas como referência, a primeira rodada parte de wireframes CSS e da auditoria do produto. Screenshots reais do navegador são capturados no Playwright (desktop/mobile). Quando houver referência de tela, transformar em alterações concretas de `src/App.jsx` e `src/styles.css`; nunca apenas aproximar com uma imagem renderizada sem componentes editáveis.

Checklist para cada PR: contraste/foco, navegação teclado, formulário, loading/empty/error, overflow 320px, desktop, captura visual e testes de importação/exportação.

## Complemento: interface Web/Páginas públicas
A edição web segue os mesmos tokens de base `src/styles.css` e adota componentes `web-*` em `src/web-styles.css`: navegação horizontal, hero compacto, seção de edição com duas colunas, etapa visível e área de upload clicável. O modo web deve declarar claramente seus limites de duração, qualidade e privacidade antes da exportação. **Nunca mostrar números fictícios nem integração remota inexistente**.

Regras: ações com estado desabilitado explícito; radio nativo para 9:16/16:9; erro próximo ao botão; `aria-live` no progresso; labels associadas a inputs; drag-and-drop ainda não prometido; responsividade 320px+; screenshots com Playwright. Pré-visualização do vídeo em `<video controls playsInline>` e exportação via WebAssembly, sem chamadas `/api`.

## Componente FilmstripTimeline

Implementação compartilhada: `src/components/VideoTimeline.jsx` e `src/components/timeline.css`. O usuário vê frames extraídos do próprio vídeo; nunca usar imagens decorativas que pareçam quadros reais. Dois sliders `input type=range` complementam os controles numéricos preexistentes e mantêm seus nomes acessíveis. A fila permite mover/remover cinco trechos sem alterar a fonte. Vídeos continuam locais e nenhuma miniatura é enviada a serviços. Gerar miniaturas de forma limitada (8 JPEGs pequenos) e cancelar a operação ao trocar mídia. O botão de exportação usa a fila apenas quando contém itens; não misturar a seleção corrente silenciosamente na sequência.

## Projeto portátil e modo roteiro

`src/components/ProjectExchange.jsx` possui dois controles de teclado reais (botões) para baixar/upload de JSON e uma explicação explícita de que o arquivo não contém mídia. `src/components/StoryStudio.jsx` fornece campo de roteiro rotulado, botão de organização, cenas numeradas, títulos e textos editáveis, duração, prévia de voz e estados acessíveis. Utilizar tokens existentes. Não chamar segmentação determinística de roteiro de “IA geradora” nem apresentar síntese Web Speech como MP4 narrado na web.

## Storyboard 2.4
Previews visuais por cena devem ser identificadas como cartões de composição (não fotografia gerada por IA). Manter label, select e file input associados; fotos são opt-in e nunca enviadas ao Pages. A disponibilidade do Piper e do motor do sistema aparece separadamente na UI; não prometer que a prévia Web Speech reproduz exatamente a voz neural da exportação. O recurso de fade respeita o fluxo de montagem e permite corte direto para ritmo mais rápido.

## Editor de legendas
`src/components/SubtitleStudio.jsx` expõe importação/exportação de arquivos com botões acessíveis, campos numéricos por cue e validação visível de limites/sobreposição. A prévia de vídeo utiliza overlay com `pointer-events:none`; legendas completas continuam no formulário editável. Não usar IA remota, não enviar texto ou mídia ao Pages. Nunca prometer burn-in na web antes de existir implementação testada.
