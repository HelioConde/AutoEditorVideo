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
