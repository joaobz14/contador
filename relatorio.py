"""
relatorio.py
Monta textos legiveis (para o bot do Telegram) a partir dos dados do nucleo.
Funcoes puras, sem dependencia do Telegram nem de rede -> faceis de testar.
"""

from __future__ import annotations

import html
from collections import defaultdict
from datetime import datetime

import separador_etiquetas_ml as core

# --------------------------------------------------------------------------
# HTML do Telegram (parse_mode="HTML")
#
# So estas tags existem: b i u s a code pre blockquote tg-spoiler. NAO ha
# lista, tabela, <br>, <div>, <span> nem CSS — quebra de linha e "\n".
# Alinhamento de coluna SO funciona dentro de <pre> (fonte monoespacada);
# fora dele a fonte e proporcional e o alinhamento se perde.
# Texto dinamico (SKU, nome de conta) TEM de ser escapado: um "&" ou "<" solto
# faz a API devolver 400 e a mensagem simplesmente nao chega.
# --------------------------------------------------------------------------
LIMITE_TELEGRAM = 4096
LIMITE_SEGURO = 3900          # folga para o rodape e o aviso de corte
DIVISOR = "━" * 16
HORA_CORTE = "08h30"          # o "pos-horario" do alerta, no texto do resumo


def esc(texto) -> str:
    """Escapa &, < e > — obrigatorio em TODO texto dinamico do HTML do Telegram."""
    return html.escape(str(texto), quote=False)


def _un(n: int) -> str:
    return f"{n} unidade" if n == 1 else f"{n} unidades"


def _sku(n: int) -> str:
    return f"{n} SKU" if n == 1 else f"{n} SKUs"


def texto_grupos(grupos: list, titulo: str) -> str:
    """Lista os grupos (SKU + quantidade) agrupados por quantidade do pedido."""
    if not grupos:
        return f"{titulo}: nenhum grupo para imprimir. 🎉"

    total_et = sum(g.total_etiquetas for g in grupos)
    linhas = [f"{titulo} — {len(grupos)} grupo(s), {total_et} etiqueta(s)"]

    por_qtd: dict[int, list] = defaultdict(list)
    for g in grupos:
        por_qtd[g.quantidade].append(g)

    for qtd in sorted(por_qtd):
        linhas.append(f"\nQuantidade por pedido = {qtd}:")
        for g in por_qtd[qtd]:
            linhas.append(f"  {g.total_etiquetas:>3}  {g.nome}")
    return "\n".join(linhas)


def texto_resumo(prontos: list, hoje: str, amanha: str) -> str:
    """Quantos pacotes ha em cada dia de despacho (Mercado Livre)."""
    linhas_dia = core.resumo_por_dia(prontos)
    return _formatar_resumo(linhas_dia, len(prontos), hoje, amanha,
                            loja="Mercado Livre")


def texto_resumo_contagem(contagem: dict, hoje: str, amanha: str, *, loja: str) -> str:
    """Mesmo resumo, a partir de uma contagem {dia: n} ja pronta (Shopee:
    contagem_por_dia vem da MESMA busca, sem rede extra). Dia "" = sem data."""
    linhas_dia = sorted(((d or "(sem data)"), n) for d, n in contagem.items())
    return _formatar_resumo(linhas_dia, sum(contagem.values()), hoje, amanha,
                            loja=loja)


def _formatar_resumo(linhas_dia, total: int, hoje: str, amanha: str, *, loja: str) -> str:
    """Layout unico do resumo por dia, com a LOJA no titulo (o resumo respeita a
    loja ativa do chat — sem o rotulo, um resumo Shopee pareceria do ML)."""
    if not linhas_dia:
        return f"Nenhum envio pronto para imprimir ({loja})."
    saida = [f"Resumo por dia de despacho — {loja} (hoje = {hoje})\n"]
    for data, qtd in linhas_dia:
        marca = "  <= HOJE" if data == hoje else ("  <= amanha" if data == amanha else "")
        saida.append(f"  {data}   {qtd:>3} pacote(s){marca}")
    saida.append(f"\nTotal: {total} pacote(s) em {len(linhas_dia)} dia(s).")
    return "\n".join(saida)


def texto_bom_dia(prontos: list, hoje: str, amanha: str) -> str:
    """Mensagem do aviso automatico da manha: manchete com a contagem de hoje
    seguida do resumo por dia."""
    de_hoje = sum(1 for p in prontos if (p.get("_envio") or {}).get("expected_date") == hoje)
    cabecalho = f"Bom dia! Hoje voce tem {de_hoje} pacote(s) para despachar."
    return f"{cabecalho}\n\n{texto_resumo(prontos, hoje, amanha)}"


def texto_alerta_pos_horario(conta: str, itens: list) -> str:
    """Alerta de venda nova ja pronta (ready_to_print) com despacho HOJE,
    detectada pelo poll automatico do bot — fora do fluxo normal de
    'Atualizar' da tela. Mostra SKU + quantidade total (somada por SKU, sem o
    numero do envio — o dono precisa saber O QUE repor com o fornecedor, nao
    qual pedido especifico)."""
    cabecalho = f"🔔 Venda {conta}" if conta else "🔔 Venda nova"
    por_sku: dict[str, int] = defaultdict(int)
    ordem: list[str] = []
    for it in itens:
        if it.chave not in por_sku:
            ordem.append(it.chave)
        por_sku[it.chave] += it.quantidade
    linhas = [cabecalho] + [f"{chave} - {por_sku[chave]}" for chave in ordem]
    return "\n".join(linhas)


def texto_resumo_vendas_apos(itens_por_conta: dict, *, agora=None,
                             contas=None, ordem=None) -> str:
    """Junta TUDO que o alerta pos-horario ja avisou HOJE (todas as contas)
    numa mensagem so. Motivado por: varias vendas caindo depois das 8:30 no
    mesmo dia viram um alerta separado cada uma, poluindo o chat — este resumo
    agrega sob demanda. `itens_por_conta` vem do estado persistido pelo alerta
    (`{conta: [{chave, quantidade}, ...]}`, ja acumulado a cada disparo) — nao
    refaz nenhuma chamada de API, so relê o que ja foi avisado.

    Devolve **HTML** (mandar com `parse_mode="HTML"`): cabecalho com a janela de
    tempo, um bloco por conta com subtotal, a lista de SKUs num `<pre>` (a unica
    forma de alinhar coluna no Telegram) ordenada por quantidade DECRESCENTE, e
    o total geral no rodape.

    `contas` (opcional) lista as contas que DEVEM aparecer mesmo sem venda —
    ausencia tambem e informacao ("nenhuma venda" e diferente de "sumiu o
    bloco"). Sem ela, so aparecem as que tem venda.

    `ordem` (opcional) e a lista de SKUs da aba Nomes: ordena o bloco TOTAL POR
    SKU na ordem de separacao (a mesma da tela e do PDF do resumo do dia). Os
    blocos por conta seguem por quantidade — sao coisas diferentes: um responde
    "o que mais vendeu", o outro "por onde eu passo pra separar".

    A mensagem SEMPRE cabe em uma so: o que passar do limite vira
    "… e mais X SKUs (Y un)". Isso e requisito, nao conveniencia — dividir o
    texto partiria um `<pre>` no meio e a API devolveria 400.
    """
    por_conta = {c: _somar(itens_por_conta.get(c) or []) for c in
                 _ordem_contas(itens_por_conta, contas)}
    if not any(por_conta.values()):
        return "Nenhuma venda avisada hoje ainda."

    agora = agora or datetime.now(core.TZ_BR)
    total_geral = sum(sum(s.values()) for s in por_conta.values())

    cabecalho = (f"🧾 <b>RESUMO DE VENDAS</b>\n"
                 f"<i>desde {HORA_CORTE} · {agora:%d/%m}, {agora:%H:%M}</i>")
    rodape = f"{DIVISOR}\n<b>TOTAL: {_un(total_geral)}</b>"
    consolidado = _consolidar(por_conta, ordem)

    # Corta pelos maiores ate caber: o teto vale para a mensagem INTEIRA, entao
    # o limite por bloco vai baixando ate o texto entrar no limite.
    for teto in (None, 25, 15, 10, 6, 3):
        partes = [_bloco(conta, somas, teto) for conta, somas in por_conta.items()]
        if consolidado:
            partes.append(_bloco_total_sku(consolidado, teto))
        texto = f"{cabecalho}\n\n" + "\n".join(partes) + f"\n{rodape}"
        if len(texto) <= LIMITE_SEGURO:
            return texto
    return texto            # ja no teto minimo: melhor curto que nao enviar


def _consolidar(por_conta: dict, ordem=None) -> dict[str, int]:
    """Soma o mesmo SKU entre as contas — vazio quando so ha uma com venda.

    E o numero que responde "quanto preciso repor deste produto": com duas
    contas, `M120INX 3` numa e `2` na outra obriga a somar de cabeca. Com uma
    conta so, o bloco repetiria a lista dela e viraria ruido.

    `ordem` (lista de SKUs da aba Nomes) manda na ordenacao deste bloco: ele e
    uma lista de SEPARACAO, e a aba Nomes e a ordem em que o dono anda pelo
    estoque. Os blocos POR CONTA continuam por quantidade — la a pergunta e
    "o que mais vendeu", nao "por onde eu passo". SKU fora da lista vai pro
    fim em ordem natural (mesma regra de `core.ordenar_grupos` e
    `historico.resumo_do_dia`).
    """
    com_venda = [s for s in por_conta.values() if s]
    if len(com_venda) < 2:
        return {}
    somas: dict[str, int] = defaultdict(int)
    for s in com_venda:
        for sku, qtd in s.items():
            somas[sku] += qtd
    if ordem:
        pos = {sku: i for i, sku in enumerate(ordem)}
        fim = len(ordem)
        chave = lambda kv: (pos.get(kv[0], fim), core._natural(kv[0]))  # noqa: E731
    else:
        chave = lambda kv: (-kv[1], kv[0])  # noqa: E731 - sem ordem: maior primeiro
    return dict(sorted(somas.items(), key=chave))


def _bloco_total_sku(somas: dict[str, int], teto: int | None) -> str:
    """Soma de todas as contas por SKU — a lista de reposicao."""
    titulo = (f"{DIVISOR}\n📦 <b>TOTAL POR SKU · "
              f"{_un(sum(somas.values()))} · {_sku(len(somas))}</b>")
    return f"{titulo}\n{_tabela(somas, teto)}\n"


def _ordem_contas(itens_por_conta: dict, contas) -> list:
    """Contas com venda primeiro (na ordem em que apareceram), depois as sem."""
    vistas = list(itens_por_conta)
    for c in (contas or []):
        if c not in vistas:
            vistas.append(c)
    return vistas


def _somar(itens: list) -> dict[str, int]:
    """SKU -> quantidade, ja ordenado por quantidade DECRESCENTE.

    Empate desempata pelo SKU (ordem estavel): sem isso, dois SKUs de mesma
    quantidade trocariam de lugar entre dois envios do mesmo dia, e o dono leria
    isso como "mudou alguma coisa".
    """
    somas: dict[str, int] = defaultdict(int)
    for it in itens:
        somas[it["chave"]] += it["quantidade"]
    return dict(sorted(somas.items(), key=lambda kv: (-kv[1], kv[0])))


def _bloco(conta, somas: dict[str, int], teto: int | None) -> str:
    """Um bloco de conta: divisor, cabecalho com subtotal e a lista no <pre>."""
    # MAIUSCULA ANTES de escapar: `esc()` primeiro produziria "&AMP;" (entidade
    # quebrada -> 400 na API). Bug pego no teste de caractere perigoso.
    nome = esc(str(conta).upper()) if conta else "GERAL"
    if not somas:
        return f"{DIVISOR}\n🏪 <b>{nome}</b>\n<i>nenhuma venda</i>\n"

    unidades = sum(somas.values())
    titulo = f"{DIVISOR}\n🏪 <b>{nome} · {_un(unidades)} · {_sku(len(somas))}</b>"
    return f"{titulo}\n{_tabela(somas, teto)}\n"


def _tabela(somas: dict[str, int], teto: int | None) -> str:
    """A lista SKU/quantidade dentro de `<pre>` — o unico lugar do Telegram onde
    coluna alinha (fonte monoespacada)."""
    itens = list(somas.items())
    if teto is None or len(itens) <= teto:
        mostrados, resto = itens, []
    else:
        # QUEM aparece e escolhido pela QUANTIDADE; a ORDEM de exibicao e a que
        # veio. Nos blocos por conta da no mesmo (ja vem por quantidade), mas no
        # TOTAL POR SKU — que vem na ordem da aba Nomes — cortar por posicao
        # jogaria fora o fim da caminhada, que pode ter os maiores. Perder o
        # maior de todos por ele estar na ultima prateleira seria absurdo.
        maiores = {s for s, _ in sorted(itens, key=lambda kv: (-kv[1], kv[0]))[:teto]}
        mostrados = [kv for kv in itens if kv[0] in maiores]
        resto = [kv for kv in itens if kv[0] not in maiores]
    # Largura vinda do SKU mais longo MOSTRADO (nao um numero fixo): SKU curto
    # nao deixa buraco e SKU longo nao empurra a coluna para fora.
    larg_sku = max(len(s) for s, _ in mostrados)
    larg_qtd = max(len(str(q)) for _, q in mostrados)
    # Preenche ANTES de escapar (parece invertido, mas e o certo): o Telegram
    # RENDERIZA "&amp;" como 1 caractere, entao a largura tem de ser medida no
    # texto cru. Escapar primeiro faria "A&B" virar 5 caracteres e desalinhar a
    # coluna na tela, apesar de o codigo "parecer" alinhado.
    linhas = [f"{esc(s.ljust(larg_sku))}  {q:>{larg_qtd}}" for s, q in mostrados]

    if resto:
        linhas.append(f"… e mais {_sku(len(resto))} ({sum(q for _, q in resto)} un)")
    return f"<pre>{chr(10).join(linhas)}</pre>"


def texto_detalhe(itens: list, chave: str) -> str:
    """Composicao de um SKU: quais produtos/variacoes/voltagens o formam e
    quantos envios de cada. Casa a chave sem diferenciar maiusculas/minusculas."""
    alvo = chave.strip().lower()
    comp: dict[tuple, set] = defaultdict(set)
    for it in itens:
        if it.chave.lower() == alvo and it.shipment_id:
            comp[(it.item_id, (it.titulo or "")[:50], it.voltagem)].add(it.shipment_id)
    if not comp:
        return f"Nada encontrado para o SKU '{chave}' hoje."
    linhas = [f"Composicao de {chave} (hoje):"]
    for (iid, tit, volt), ships in sorted(comp.items(), key=lambda x: -len(x[1])):
        v = f" [{volt}]" if volt else ""
        linhas.append(f"  {len(ships):>3}  {iid}  {tit}{v}".rstrip())
    return "\n".join(linhas)


def dividir_mensagem(texto: str, limite: int = 4000) -> list[str]:
    """Divide um texto em blocos <= limite (o Telegram corta em ~4096), quebrando
    preferencialmente em linhas. Linhas isoladas maiores que o limite sao
    fatiadas no tamanho maximo."""
    blocos: list[str] = []
    atual = ""
    for linha in texto.split("\n"):
        while len(linha) > limite:               # linha gigante: fatia na marra
            if atual:
                blocos.append(atual)
                atual = ""
            blocos.append(linha[:limite])
            linha = linha[limite:]
        if not atual:
            atual = linha
        elif len(atual) + 1 + len(linha) <= limite:
            atual = f"{atual}\n{linha}"
        else:
            blocos.append(atual)
            atual = linha
    if atual:
        blocos.append(atual)
    return blocos or [""]
