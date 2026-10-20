# Padrões deste projeto

Antes de alterar componentes ou CSS, leia docs/DESIGN_SYSTEM.md. Siga Vercel Web Interface Guidelines e WCAG 2.2: componentes semânticos, controle por teclado, foco visível, conteúdo local em pt-BR, sem controles inertes, responsividade 320px+ e estados carregando/erro/vazio. Use design tokens; não invente estatísticas ou sinalize recursos futuros como implementados.

Para qualquer mudança funcional: npm run check e npm run test:e2e, com captura de tela em desktop e mobile. API deve escutar apenas 127.0.0.1, não permitir SSRF ou caminhos baseados em nomes de upload, e nunca gravar mídia no Git.
