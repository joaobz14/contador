# Auditoria completa — 2026-07-16

> Diagnóstico somente-leitura (nenhum código alterado). Base: CLAUDE.md,
> `docs/ARQUITETURA.md` (12 invariantes), `docs/PRIORIDADES_TECNICAS.md`,
> `docs/CHANGELOG.md` (achados já corrigidos NÃO re-listados), grafo
> `graphify-out/` e leitura integral dos 10 módulos + testes. Suíte executada
> neste ambiente: **293 passed, 3 skipped** (os 3 pulam sem o
> `python-telegram-bot` local; no CI com o bot instalado a contagem sobe para
> a casa dos ~310). Duas hipóteses de risco foram **provadas dinamicamente**
> (script descartável, ver achados A3 e A5).
>
> **Resumo honesto:** nenhum achado CRÍTICO. As 12 invariantes estão, no
> geral, garantidas por barreiras de código + testes-guardiões — o trabalho
> das auditorias anteriores segurou. O que sobra são lacunas *entre* as
> invariantes (duplicidade física que o estado não cobre), um ponto de
> dessincronização do bot multi-processo e higiene de robustez/qualidade.

---

## 1. Invariantes × código real

| # | Invariante | Veredito | Evidência / lacuna |
|---|---|---|---|
| 1 | GUI nunca marca antes da confirmação | ✅ Garantida | Único call-site de `prov.marcar_impresso` é `_confirmar_e_marcar` (separador_gui.py:885); interface de provedor sem `imprimir_grupo` + teste-guardião (tests/test_provedores.py:74); `test_gerar_zip_lotes_nao_marca_estado`. A barreira é a convenção do provedor — um botão novo que importasse `core.imprimir_pendentes` direto ainda a furaria, mas isso exige ato deliberado. |
| 2 | Reimpressão não altera estado | ✅ Garantida | `core.reimprimir` / `shopee.reimprimir_grupo` / `ProvedorMLAmbas.reimprimir` não tocam estado; testado. |
| 3 | Estado por marketplace+conta+dia | ⚠️ Garantida com 2 ressalvas | Chave `{dia}\|{chave}\|q{qtd}` ok. Ressalvas: o "dia" depende de `definir_conta`/carimbo de `g.dia` feitos pelo chamador — ver A2 (bot dessincronizado) e A6 (hoje implícito na virada do dia). |
| 4 | Envio novo reabre como parcial | ✅ Garantida | `estado.status_grupo` compara envios atuais × impressos; `test_envio_novo_reabre_como_parcial`. |
| 5 | Merge + trava no ciclo ler→mesclar→salvar; poda relê sob trava | ✅ Garantida | estado.py:238-242 e :284-288; tests/test_estado_comum.py:104, :231 (arquivo real), :262 (poda). |
| 6 | Token sempre via `obter_token` | ✅ Garantida | Grep: `renovar_token` só é chamado dentro dos dois `obter_token` (separador_etiquetas_ml.py:409, shopee_api.py:258) e em testes. `tentativas=1` protegido por teste (tests/test_robustez.py:240). |
| 7 | Refresh serializado (threads + processos, espera 2×TIMEOUT) | ✅ Garantida | Lock + trava de arquivo nos dois `obter_token`; 4 cenários do msvcrt fake (tests/test_estado_comum.py:180-228). Ressalva menor: no caminho degradado (FS sem trava) volta ao modelo "relê o disco", janela residual conhecida e documentada. |
| 8 | Etiqueta Shopee só após organizar/AWB | ✅ Garantida | `_organizar_varios` em camadas; confirmação pelo AWB, não pela resposta do batch. |
| 9 | `create_shipping_document` exige tracking | ✅ Garantida | `gerar_etiqueta` aborta com mensagem clara se falta AWB (shopee_api.py:569-574); `criar_documento` envia o tracking. |
| 10 | Bot não imprime Shopee | ✅ Garantida | Dupla checagem `_lista_imprimivel` em `_confirmar_impressao` E `_executar_impressao`; Shopee nem recebe teclado de impressão (bot_telegram.py:348-349); testado. |
| 11 | Bot não imprime grupo antigo após troca de conta/loja | ⚠️ Furada num cenário | `_conta_mudou` compara config×config — não detecta que o próprio bot está *servindo* a conta antiga depois de a GUI trocar a ativa. Ver **A2**. Troca de loja está ok (`loja_grupos`). |
| 12 | Segredos nunca versionados | ✅ Garantida | `.gitignore` cobre credenciais, `.bak`, `.tmp` (inclusive o com PID), `.lock`, logs, caches, config. |

---

## 2. Achados

### [ALTO] A1 — GUI imprime a partir de estado defasado (da última coleta)

- **Arquivo:** separador_gui.py:879 (`self.prov.imprimir_lotes(grupos, self.estado, …)`; vale para `imprimir`, `imprimir_lotes` e `imprimir_proximo`)
- **Problema:** os "pendentes" de cada grupo são calculados sobre `self.estado`, lido no último Atualizar — a GUI não relê o disco antes de gerar.
- **Impacto operacional:** se o bot (outro processo) imprimiu o mesmo grupo entre o Atualizar e o clique, a GUI baixa e manda de novo as mesmas etiquetas → **papel duplicado físico** (o estado em si não se perde: o merge sob trava une as marcações — mas o pacote pode sair etiquetado em dobro). A janela é de minutos a horas (tela aberta desde a coleta da manhã).
- **Correção sugerida:** no início de `_gerar_sem_marcar_thread`, recarregar `self.estado = self.prov.carregar_estado()` antes de calcular pendentes (1 linha; a trava e o merge já cobrem o resto).
- **Invariante:** nenhuma é violada formalmente — é a lacuna *entre* as inv. 2 e 5 (elas protegem a marcação, não a duplicidade física); hoje depende da disciplina de clicar Atualizar antes de imprimir.

### [MÉDIO] A2 — Bot não acompanha a troca de conta feita pela GUI (inv. 11 passa em falso)

- **Arquivo:** bot_telegram.py:343 (`chat_data["conta"] = core.conta_ativa()`) + :364 (`_conta_mudou`) vs. :640-643 (sincronização só no startup)
- **Problema:** `conta_ativa()` lê o `config.json` fresco, mas os globais do processo do bot (`ARQUIVO_CRED`/`ARQUIVO_ESTADO`) só mudam com `definir_conta` — que o bot roda apenas no startup e no `/conta`. Se a **GUI** troca a conta ativa, o bot continua coletando/imprimindo a conta **antiga**, e a listagem carimba `chat_data["conta"]` com o valor **novo** do config — então `_conta_mudou` compara "novo == novo" e deixa imprimir.
- **Impacto operacional:** o bot lista e imprime pedidos da conta antiga se apresentando como a nova (token/estado internamente consistentes — sem corrupção — mas o operador acha que está na outra conta; `/conta` também exibe o nome errado). O teste existente (tests/test_bot_impressao.py:181) cobre só a troca feita *depois* da listagem.
- **Correção sugerida:** no início de cada coleta/impressão do bot, re-sincronizar (`_garantir_conta_ativa()` ou `definir_conta(core.conta_ativa())`) e carimbar `chat_data["conta"]` com a conta **realmente usada** na coleta, não a do config.
- **Invariante:** 11 (e indiretamente 3 — o "por conta" depende do global sincronizado).

### [MÉDIO] A3 — Estado corrompido (≠ ausente) silencia todas as marcas de impresso — *provado dinamicamente*

- **Arquivo:** estado.py:54 (`ler_json` → `{}` em corrupção) + :274-282 (`_ciclo` regrava o disco cru)
- **Problema:** um `estado_grupos.json`/`estado_shopee.json` corrompido (antivírus, disco, edição manual — a gravação do app é atômica+fsync, então a causa seria externa) é lido como `{}` **sem nenhum aviso**, indistinguível de "nunca imprimi nada"; e a próxima marcação **substitui** o arquivo corrompido, destruindo o que era recuperável.
- **Impacto operacional:** todos os grupos do dia voltam a PENDENTE → reimpressão em massa sem que o operador saiba o porquê. (Prova: JSON truncado → `ler_json`=`{}`; `carregar` não avisa; `marcar_impresso` regravou só a chave nova.)
- **Correção sugerida:** distinguir corrupção de ausência em `ler_json` (ex.: renomear o corrompido para `.corrupto` e logar/avisar via `registro`), ou dar ao estado o mesmo espelho `.bak` das credenciais.
- **Invariante:** 2/5 na prática (a consequência é reimpressão e perda de histórico).

### [MÉDIO] A4 — Colisão de nome do ZIP na pasta Downloads engole um lote

- **Arquivo:** separador_etiquetas_ml.py:1209-1213 (`_gerar_zip`, ex.: `etiqueta de envio - LOTES_x2.zip` + `tmp.replace` sobrescrevendo); shopee_api.py:625-630 tem o mesmo padrão (`lote {sn} xN`)
- **Problema:** o nome do ZIP é determinístico e a gravação sobrescreve silenciosamente; dois lotes com o mesmo rótulo (ex.: dois "LOTES x2" seguidos) gerados antes de o app da Zebra consumir o primeiro fazem o segundo **substituir** o primeiro.
- **Impacto operacional:** um lote nunca imprime, e a GUI acredita que enviou (o operador confirma "saiu certo?" olhando o papel — a defesa humana existe, mas com o monitor da Zebra desligado/lento os arquivos se acumulam e a perda passa batida).
- **Correção sugerida:** acrescentar um sufixo único (hora `%H%M%S` ou contador) ao nome, preservando o prefixo que a Zebra reconhece.
- **Invariante:** nenhuma; área de risco "Pasta Downloads / app Zebra" da ARQUITETURA.

### [BAIXO] A5 — `estado_shopee.json` nunca é podado em disco (cresce sem fim) — *provado dinamicamente*

- **Arquivo:** shopee_api.py:762 (`persistir_poda=False`) + estado.py:275-281 (o `_ciclo` regrava o **disco cru**, não a visão podada)
- **Problema:** a poda da Shopee é só em memória; cada `marcar_impresso` regrava o arquivo com as entradas antigas intactas (prova: chave de 2020 sobreviveu à marcação). O ML não sofre disso (poda persistida no Atualizar).
- **Impacto operacional:** crescimento lento porém sem limite (~KB/ano no volume atual — anos até incomodar); o cache de AWB, podado contra a visão em memória, permanece correto.
- **Correção sugerida:** `persistir_poda=True` também na Shopee (a trava já protege a regravação) ou podar dentro do `_ciclo` antes de salvar.
- **Invariante:** nenhuma; higiene da inv. 5.

### [BAIXO] A6 — "Hoje implícito" do bot/CLI marca no dia errado na virada da meia-noite

- **Arquivo:** separador_etiquetas_ml.py:970-974 (`coletar_grupos` só carimba `g.dia` quando `dia is not None`) + estado.py:166 (`grupo.dia or _hoje_br()` avaliado na hora de marcar)
- **Problema:** `/hoje` no bot (e `listar` no CLI) produz grupos com `dia=""`; um grupo listado 23:50 e impresso 00:10 marca a chave sob o **dia novo**, enquanto o despacho é do dia anterior.
- **Impacto operacional:** na GUI (que usa o dia real de despacho) o grupo reaparece pendente → risco de reimpressão. É a extensão do caso "Sem data" já documentado na ARQUITETURA, mas pelo caminho do bot — cenário raríssimo (impressão cruzando a meia-noite).
- **Correção sugerida:** carimbar `g.dia = hoje` também no ramo `somente_hoje` de `coletar_grupos` (não colide com a poda: a data é válida).
- **Invariante:** 3.

### [BAIXO] A7 — `zpl_divisoria` emite `^CI28` sem o reset `^CI0`

- **Arquivo:** separador_etiquetas_ml.py:1161
- **Problema:** o carimbo teve o cuidado de resetar (`^CI0`) porque o `^CI` **persiste entre etiquetas** — a divisória liga UTF-8 e não desliga, então todas as DANFEs/etiquetas de envio depois de uma divisória são interpretadas em `^CI28`.
- **Impacto operacional:** se algum conteúdo gerado pelo ML depender do encoding padrão da Zebra, acentos podem sair corrompidos nas etiquetas seguintes à divisória (assimetria com o próprio racional documentado do carimbo; pode nunca ter se manifestado porque o conteúdo do ML é praticamente ASCII).
- **Correção sugerida:** encerrar a divisória com `^CI0` antes do `^XZ` (simétrico ao carimbo).
- **Invariante:** nenhuma; convenção de encoding do CLAUDE.md.

### [BAIXO] A8 — `sem_segredos` só cobre segredos em formato query-string

- **Arquivo:** registro.py:41-42
- **Problema:** a regex redige `chave=valor`; um segredo em forma JSON (`"refresh_token": "…"`) ou `client_secret`/`partner_key` não seriam redigidos. Hoje **nenhum caminho conhecido** os coloca em texto de exceção (POSTs levam segredo no corpo, não na URL; `_rede_limpa`/`_levantar_se_erro` cortam a URL assinada) — é defesa em profundidade fina.
- **Impacto operacional:** um caminho de erro futuro que serialize o corpo/credencial (ex.: `f"Falha: {dados}"` com eco do request) passaria batido pelas duas camadas de redação.
- **Correção sugerida:** ampliar a regex para o par JSON (`"(access|refresh)_token"\s*:\s*"…"`) e incluir `client_secret`/`partner_key`.
- **Invariante:** apoia a 12.

### [BAIXO] A9 — CLI Shopee `etiqueta <order_sn>` gera sem marcar estado

- **Arquivo:** shopee_api.py:966-978
- **Problema:** o comando gera/baixa a etiqueta (organiza implicitamente? não — exige AWB pronto ou falha) e **não marca** o pedido como impresso; o CLAUDE.md afirma "Bot/CLI marcam direto".
- **Impacto operacional:** um pedido impresso pelo CLI continua PENDENTE na tela → o operador pode reimprimi-lo no lote seguinte.
- **Correção sugerida:** decidir e alinhar: ou marcar após gerar (consistente com o resto do CLI), ou documentar o comando explicitamente como diagnóstico que não marca.
- **Invariante:** divergência doc↔código (regra do CLAUDE.md, não uma das 12).

### [BAIXO] A10 — Bot congela as preferências lidas no startup

- **Arquivo:** bot_telegram.py:640 (`aplicar_config()` só no `main`)
- **Problema:** além da conta (A2), o `MODO_IDENT`/`CARIMBAR_SKU` do bot é o do momento da abertura; trocar a identificação na GUI não afeta o bot até reiniciar.
- **Impacto operacional:** etiquetas impressas pelo bot saem com o carimbo antigo (divergência silenciosa com a tela; o CHANGELOG promete "igual à tela").
- **Correção sugerida:** chamar `aplicar_config()` no início de `_imprimir_grupo` (barato: 1 leitura de JSON local).
- **Invariante:** nenhuma.

### [BAIXO] A11 — `chat_ids` malformado derruba o bot na abertura com traceback cru

- **Arquivo:** bot_telegram.py:93 (`{int(c) for c in cfg.get("chat_ids", [])}`)
- **Problema:** um valor não numérico no `bot_config.json` (editado à mão) gera `ValueError` fora do ramo de erro amigável.
- **Impacto operacional:** o bot não sobe e a mensagem é um traceback genérico (no modo auto-restart, loop de crash com o motivo só no `bot.log`).
- **Correção sugerida:** validar/ignorar entradas inválidas com aviso claro (mesmo espírito do `_sanear_config`).
- **Invariante:** nenhuma.

### [BAIXO] A12 — CI sem linter

- **Arquivo:** .github/workflows/testes.yml
- **Problema:** o workflow roda pytest + gui-smoke, mas nenhum linter (ruff/flake8) — imports mortos, sombras de nome e estilo só aparecem em revisão manual.
- **Impacto operacional:** regressões de higiene entram sem check vermelho (o histórico já registrou "remoção de imports mortos" achada à mão).
- **Correção sugerida:** job `ruff check .` (segundos de execução; começar com regras E/F já paga).
- **Invariante:** nenhuma.

### [BAIXO] A13 — Máquina de token duplicada entre núcleo e `shopee_api`

- **Arquivo:** separador_etiquetas_ml.py:341-409 × shopee_api.py:206-258
- **Problema:** `renovar_token`/`_token_valido`/`obter_token` (lock, double-check, trava, espera 2×TIMEOUT, MARGEM_TOKEN) existem em duas cópias quase idênticas — a correção da trava precisou ser aplicada duas vezes.
- **Impacto operacional:** o próximo fix de token pode ser aplicado em um lado só (o par já divergiu no passado antes das auditorias).
- **Correção sugerida:** extrair um `token.py` comum path-parametrizado, no mesmo molde do `estado.py` (encaixa nas PRIORIDADES §1/§2); baixa urgência — os dois lados estão corretos e testados hoje.
- **Invariante:** apoia a 6/7.

---

## 3. Confirmações pedidas (sem achado novo)

- **God-file (`separador_etiquetas_ml.py`)** — diagnóstico de PRIORIDADES §1 **confirmado e ainda válido**: 1.480 linhas concentrando API ML, token, credenciais, config/multi-conta, cache, identidade, agrupamento, ZPL/carimbo, ZIP e CLI. A extração do `estado.py` (§2) já saiu; o restante segue como maior superfície de risco a mudanças. Nada a acrescentar aqui além do A13 (token seria a próxima extração natural).
- **Código morto** — não encontrei função sem uso (consistente com a auditoria anterior). `Grupo.rastreio` (singular) e `CARIMBAR_SKU` são compat deliberada e ainda referenciados; `buscar_pedidos_amplo`/`rastrear_sku`/`parametros_documento` são diagnósticos de CLI vivos.
- **O que os testes NÃO cobrem** — o caminho **real** do `msvcrt` (coberto só por fakes; o CI é POSIX — risco residual aceito e documentado); os fluxos interativos completos da GUI (`_render`, seleção, busca — o smoke cobre import/inicialização/screenshot, e a lógica sensível foi extraída para funções puras testadas); os wrappers async do bot (as funções síncronas são testadas; 3 testes dependem do pacote telegram e só rodam no CI); `pegar_token.py`/`pegar_token_shopee.py` (interativos, rodam uma vez — zero testes); e a *consequência* de corrupção do estado (há teste de tolerância em tests/test_robustez.py:29, não do efeito operacional — ver A3).
- **Dependências/Windows** — pinning saudável (`requests>=2.31,<3`, `python-telegram-bot>=20,<23`, tetos deliberados); `pytest` sem pin e sem lockfile (aceitável para o porte). Pontos frágeis Windows-only conhecidos e conscientes: heurística `_LIMIAR_OCUPADO=5s` do msvcrt (um FS de rede lento poderia ser lido como "trava ocupada" — só afeta o caminho do token e degrada com segurança), `Path.home()/"Downloads"` (redirecionamento de pasta; comentado no código como ajuste manual), `pythonw` sem console (mitigado pelo saneamento de config e pelo `registro.py`, que só adiciona StreamHandler quando há stderr).
- **Concorrência trava/handle** — verificado: cada `trava()` abre o próprio handle do `.lock` (funciona entre processos e entre threads); dentro de um mesmo processo a contenção é evitada por `_LOCK_TOKEN` (token) e pelo `ocupado`/modalidade dos diálogos (GUI); não há aquisição aninhada de travas em ordens diferentes (sem risco de deadlock).

---

## 4. FALSOS POSITIVOS DESCARTADOS

Coisas que pareciam bug mas o código/os testes já protegem:

1. **`raise_for_status` no `_get` do ML** (separador_etiquetas_ml.py:472) — a URL do ML não carrega token (vai no header `Authorization`); o caso perigoso (Shopee, token na query) usa `_levantar_se_erro`, com teste-guardião que proíbe `raise_for_status` (tests/test_shopee.py:751-752).
2. **Corrida de refresh GUI×bot** — fechada por `estado.trava` ao lado das credenciais com `espera=2×TIMEOUT`; 4 cenários Windows com msvcrt fake (tests/test_estado_comum.py:180-228) + `renovar_token` sem retry (tests/test_robustez.py:240).
3. **Perda de marcação concorrente tela×bot** — ciclo inteiro sob trava; reproduzido com processos e arquivo real (tests/test_estado_comum.py:104 e :231).
4. **Poda apagando marcação concorrente** — regravação sob a mesma trava, relendo o disco (tests/test_estado_comum.py:262).
5. **Método de provedor que marca direto** — removido, com teste-guardião que impede a volta (tests/test_provedores.py:74).
6. **Adoção inline no modo 🌐 Ambas** — re-coleta em vez de aplicar em memória (tests/test_gui_adocao.py:46); ML normal aplica local com fusão testada (:60-:87).
7. **Ambas marcando no estado/arquivo errado** — roteamento por conta com `definir_conta` antes de cada gravação (tests/test_provedores.py:114 + tests/test_ambas.py); `arquivo=`/`ler` resolvidos em tempo de chamada, então apontam para a conta certa.
8. **Falha de gravação após o "sim"** — `_marcar_lote_tolerante`: retry, isolamento por grupo, aviso "não reimprima", erros redigidos (tests/test_gui_confirmacao.py, 4 testes).
9. **Token vencido com a tela aberta há horas** — `ProvedorML._token_atual` revalida via `obter_token` a cada impressão (tests/test_provedores.py:83).
10. **Teclado do bot acima do limite do Telegram** — fatiado em ≤90 botões sem cabeçalho órfão (tests/test_bot_impressao.py).
11. **Dois processos disputando o mesmo `.tmp`** — o nome inclui o PID (tests/test_estado_comum.py:304).
12. **`config.json` inválido derrubando GUI/bot** — `_sanear_config` com os 8 casos da prova (tests/test_config.py:41-45).
13. **ZIP gerado antes da confirmação** — correto por design: gerar sem marcar É o contrato (inv. 1); a confirmação controla a *marcação*, não a geração (tests/test_lotes.py).
14. **`^CI28` do carimbo vazando para a etiqueta de envio** — o campo do carimbo reseta com `^CI0` logo após o `^FS` (tests/test_carimbo.py). (O vazamento restante é só o da divisória — A7.)
15. **`.bak` desgarrado ressuscitando credencial morta** — a migração leva o `.bak` junto e remove órfãos da raiz (tests/test_contas.py); a janela residual (falha de IO ao gravar o `.bak` deixando-o um refresh atrás) é inerente ao design de espelho e o re-sync na leitura a estreita.

---

## 5. TOP 5 prioridades por impacto

1. **A1 — Reler o estado do disco antes de gerar etiquetas na GUI** (1 linha; elimina a duplicidade física GUI×bot, o único achado ALTO).
2. **A2 — Re-sincronizar a conta do bot a cada coleta/impressão** (fecha o falso-negativo da inv. 11 e o desencontro operador↔bot em multi-conta).
3. **A3 — Tornar a corrupção do estado um evento visível** (aviso + preservar o arquivo corrompido; evita reimpressão em massa às cegas).
4. **A4 — Nome de ZIP único por geração** (sufixo de hora; fecha a janela de lote engolido na Downloads).
5. **A5 + A12 — Poda em disco do estado Shopee e linter no CI** (dois itens baratos de higiene: um fecha crescimento sem fim, o outro fecha regressões de estilo/import antes do merge).
