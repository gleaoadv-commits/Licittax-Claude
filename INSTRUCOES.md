# Rotina de publicação — Instagram @licittax

Este repositório gera e publica automaticamente conteúdo no Instagram da Licittax
(conta `17841464593621126`, conector `instagram` do Windsor.ai).

**Por dia:** 1 post no feed + 2 stories.

| Tipo | Formato | Conteúdo |
|---|---|---|
| `post` | Feed 1080x1350 | Educativo sobre licitações e/ou captação de clientes para a assessoria |
| `story-edital` | Story 1080x1920 | Um edital aberto real do PNCP + WhatsApp |
| `story-cliente` | Story 1080x1920 | Captação de clientes + WhatsApp |

- `gerar_post.py` — gera as artes (e a legenda do post).
- `config.json` — WhatsApp da Licittax: (31) 3157-6737 · wa.me/553131576737.
- `posts/` — imagens publicadas (servidas publicamente pelo GitHub, o Instagram baixa daqui).
- `historico.json` — o que já foi publicado (licitações, temas, publicações).

## Passo a passo de uma execução

1. **Repositório:** use o clone que já estiver no container (`/home/user/licittax-claude`,
   `/home/user/Licittax-Claude` ou similar); se não houver, anexe com `add_repo`
   (owner `gleaoadv-commits`, repo `licittax-claude`, access `push`) e clone.
   Sempre trabalhe sobre a `main` atualizada: `git fetch origin main && git checkout -B main origin/main`
   (o histórico vive na `main`).

2. **Gerar:**
   - **post** (feed): alterne entre *educativo* e *captação* olhando os últimos itens de
     `historico.json > dicas` (ou combine os dois: ensinar algo e terminar chamando para a
     assessoria). Escolha um tema que **não esteja** no histórico. Ideias educativas:
     modalidades, fases do pregão, habilitação, ME/EPP e LC 123, SICAF, impugnação e recurso,
     garantia contratual, reequilíbrio, atestados de capacidade técnica, dispensa,
     inexigibilidade, ata de registro de preços, PNCP, sanções, prazos. Ideias de captação:
     erros que desclassificam empresas, por que ter assessoria, como começar a vender para o
     governo, o que a Licittax faz por você, mitos sobre licitação.
     Escreva um JSON com `tema`, `selo` (ex.: "Você sabia?", "Dica Licittax", "Atenção",
     "Para sua empresa"), `titulo` (até ~60 caracteres), `itens` (3 a 5 frases curtas),
     `fonte` (dispositivo legal exato, ou omita se for post de captação sem base legal) e
     `legenda` (texto do Instagram, emojis moderados, chamada final:
     "Fale com a Licittax no direct ou no WhatsApp (31) 3157-6737 📲", hashtags terminando
     em `#licittax`). Rode `python3 gerar_post.py dica arquivo.json`.
   - **story-edital**: `python3 gerar_post.py story-edital`
   - **story-cliente**: escreva um JSON com `tema`, `selo`, `titulo` (frase de impacto,
     até ~45 caracteres), `itens` (2 a 4 benefícios curtos) e `cta` (ex.: "Fale com um
     especialista", "Peça um diagnóstico gratuito"). Varie o tema em relação a
     `historico.json > stories_cliente`. Rode `python3 gerar_post.py story-cliente arquivo.json`.

   **Só afirme o que tem certeza** sobre a Lei 14.133/2021 e normas relacionadas; cite o
   artigo. Na dúvida, escolha outro tema. Não invente números, estatísticas, depoimentos
   ou promessas de resultado (ex.: "garantimos que você vence").

3. **Conferir a imagem** gerada (abrir o JPEG): texto legível, sem sobreposição.

4. **Publicar a imagem no GitHub:**
   `git add posts historico.json && git commit -m "<tipo> <id>" && git push origin HEAD:main`.
   URL pública (use o SHA do commit):
   `https://raw.githubusercontent.com/gleaoadv-commits/licittax-claude/<SHA>/posts/<id>.jpg`
   (`<SHA>` = `git rev-parse HEAD`). Confira com `curl -sI` que responde 200 `image/jpeg`.

5. **Publicar no Instagram** com Windsor.ai `execute_action`, connector `instagram`,
   account `17841464593621126`:
   - **post** → action `create_image_post`, params `{"image_url": <URL>, "caption": <posts/<id>.txt>}`
   - **story-edital / story-cliente** → action `create_story`, params `{"image_url": <URL>}`
     (stories não têm legenda; a API não permite figurinha de link — o WhatsApp vai na arte)

   A publicação direta já está autorizada pelo dono da conta. Se o Instagram não conseguir
   baixar a imagem, aguarde ~1 min e tente de novo (até 3x).

6. **Registrar** em `historico.json > publicados` `{data, tipo, id, media_id}` e dar commit e
   `git push origin HEAD:main`.

7. Se algo falhar (PNCP fora do ar, erro do Instagram), não invente dados: registre o erro
   na resposta final da sessão.
