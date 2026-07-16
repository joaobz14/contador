"""
provedores.py
Abstrai o marketplace (Mercado Livre / Shopee) atras de uma interface comum, para
a GUI tratar os dois do mesmo jeito. Cada provedor sabe coletar os grupos, imprimir
e controlar o estado de "ja impresso" do seu jeito.

Diferencas que a interface esconde:
  - ML tem multiplas contas (Gastromaq/Cozilatti); a Shopee tem uma loja so.
  - ML carimba a DANFE (identificacao); a Shopee nao (etiqueta e imagem).
  - A Shopee precisa ORGANIZAR o envio (drop-off) antes de imprimir; o ML nao.
"""
from __future__ import annotations

import separador_etiquetas_ml as core
import shopee_api as shopee


class Provedor:
    """Interface comum. A GUI usa apenas estes metodos/atributos."""

    nome = ""
    suporta_identificacao = False   # carimbo/divisoria (so ML)
    suporta_contas = False          # sub-contas (so ML)
    organiza_envio = False          # precisa organizar antes de imprimir (so Shopee)
    # Pedidos pendentes por dia de despacho ({YYYY-MM-DD ou "": n}), preenchido a
    # cada coletar() a partir da MESMA busca (sem rede extra). A GUI usa para
    # mostrar a contagem no seletor de dias e oferecer datas fora de seg-sex.
    contagem_dias: dict

    # ---- selecao de conta (ML) -------------------------------------------
    def contas(self) -> list[str]:
        return []

    def definir_conta(self, nome: str) -> None:
        pass

    # ---- coleta / estado --------------------------------------------------
    def coletar(self, *, dia=None, somente_hoje=True, progresso=None) -> list:
        raise NotImplementedError

    def carregar_estado(self) -> dict:
        raise NotImplementedError

    def status_grupo(self, estado: dict, grupo) -> str:
        return core.status_grupo(estado, grupo)

    def envios_pendentes(self, estado: dict, grupo) -> list:
        return core.envios_pendentes(estado, grupo)

    def marcar_impresso(self, estado: dict, grupo, ids: list) -> None:
        """Marca order_sns/shipment_ids como impressos no estado do provedor."""
        raise NotImplementedError

    # ---- impressao --------------------------------------------------------
    # NAO ha imprimir_grupo aqui DE PROPOSITO: a GUI imprime tudo (individual
    # inclusive) por imprimir_lotes, que GERA SEM MARCAR — a marcacao so vem
    # depois da confirmacao fisica (invariante 1). Um metodo de grupo que
    # marcasse direto ja existiu, morto, e seria uma arma engatilhada se algum
    # botao novo o chamasse. Bot e CLI (que marcam direto por design) usam as
    # funcoes de modulo (core.imprimir_pendentes / shopee_api.imprimir_grupo).
    def imprimir_lotes(self, grupos: list, estado: dict, *, modo="nenhuma") -> tuple:
        """Imprime varios grupos SEM marcar. Devolve (impressos, falhas)."""
        raise NotImplementedError

    def reimprimir(self, grupo) -> list:
        raise NotImplementedError


class ProvedorML(Provedor):
    nome = "Mercado Livre"
    suporta_identificacao = True
    suporta_contas = True
    organiza_envio = False

    def __init__(self) -> None:
        self.cred = None
        self.token = None
        self.contagem_dias = {}

    def contas(self) -> list[str]:
        return core.listar_contas()

    def definir_conta(self, nome: str) -> None:
        core.definir_conta(nome)

    def _renovar(self) -> str:
        self.cred = core.carregar_credenciais()
        self.token = core.obter_token(self.cred)   # cache + lock (nao rotaciona a toa)
        return self.token

    def _token_atual(self) -> str:
        """Token VALIDO para imprimir/reimprimir. Nao reusar self.token cru: ele
        vem da ultima coleta e pode ter expirado (GUI aberta por horas) — o 401
        se repetiria ate um novo Atualizar. obter_token revalida a expiracao e
        so renova quando preciso (cache + lock + rele o disco)."""
        if self.cred is None:
            return self._renovar()
        self.token = core.obter_token(self.cred)
        return self.token

    def coletar(self, *, dia=None, somente_hoje=True, progresso=None) -> list:
        token = self._renovar()
        coleta = core.coletar_grupos(
            token, self.cred["seller_id"], dia=dia,
            somente_hoje=somente_hoje, progresso=progresso,
        )
        # Contagem por dia de TODOS os prontos (a busca ja trouxe tudo).
        self.contagem_dias = {
            ("" if d == "(sem data)" else d): n
            for d, n in core.resumo_por_dia(getattr(coleta, "prontos", []))
        }
        return coleta.grupos

    def carregar_estado(self) -> dict:
        return core.carregar_estado()

    def marcar_impresso(self, estado: dict, grupo, ids: list) -> None:
        core.marcar_impresso(estado, grupo, ids)

    def imprimir_lotes(self, grupos: list, estado: dict, *, modo="nenhuma") -> tuple:
        # (impressos, falhas) — o ML nao tem falha parcial, entao falhas=[].
        return core.gerar_zip_lotes(self._token_atual(), grupos, estado, modo=modo), []

    def reimprimir(self, grupo) -> list:
        return core.reimprimir(self._token_atual(), grupo)


class ProvedorShopee(Provedor):
    nome = "Shopee"
    suporta_identificacao = False
    suporta_contas = False
    organiza_envio = True

    def __init__(self) -> None:
        self.cred = None
        self.contagem_dias = {}
        # Setup unico, so usado quando algum pedido exige (ver _montar_dropoff).
        self.branch_id = None
        self.sender_real_name = None

    def _creds(self) -> dict:
        if self.cred is None:
            self.cred = shopee.carregar_credenciais()
        return self.cred

    def coletar(self, *, dia=None, somente_hoje=True, progresso=None) -> list:
        grupos, _qtd, contagem = shopee.coletar_grupos(
            self._creds(), dia=dia, somente_hoje=somente_hoje)
        self.contagem_dias = contagem
        # Rastreio (AWB) dos grupos de 1 pedido ja impresso, para conferencia.
        shopee.preencher_rastreios(self._creds(), grupos, shopee.carregar_estado())
        return grupos

    def carregar_estado(self) -> dict:
        return shopee.carregar_estado()

    def marcar_impresso(self, estado: dict, grupo, ids: list) -> None:
        shopee.marcar_impresso(estado, grupo, ids)

    def imprimir_lotes(self, grupos: list, estado: dict, *, modo="nenhuma") -> tuple:
        return shopee.imprimir_lotes(
            self._creds(), grupos, estado,
            branch_id=self.branch_id, sender_real_name=self.sender_real_name,
        )

    def reimprimir(self, grupo) -> list:
        return shopee.reimprimir_grupo(self._creds(), grupo)


# ---------------------------------------------------------------------------
# MODO "AMBAS" (Mercado Livre com todas as contas juntas)
# ---------------------------------------------------------------------------
CONTA_AMBAS = "__ambas__"   # valor-sentinela do radio "🌐 Ambas" no seletor da GUI


def fundir_grupos(grupos_por_conta: dict[str, list]) -> list:
    """Funde grupos de varias contas por (SKU/chave + quantidade): um grupo unico
    com todas as etiquetas, que lembra em `.por_conta` o sub-grupo de cada conta —
    para imprimir com o token certo e marcar no estado certo. Nome/combo vem do
    primeiro sub-grupo (o nomes_sku.json e compartilhado, entao sao iguais)."""
    fundidos: dict[tuple, core.Grupo] = {}
    for conta, grupos in grupos_por_conta.items():
        for g in grupos:
            chave = (g.chave, g.quantidade)
            f = fundidos.get(chave)
            if f is None:
                f = core.Grupo(chave=g.chave, nome=g.nome, quantidade=g.quantidade,
                               shipment_ids=[], dia=g.dia,
                               componentes=list(g.componentes))
                f.por_conta = {}
                fundidos[chave] = f
            f.shipment_ids.extend(g.shipment_ids)
            f.por_conta[conta] = g
    return core.ordenar_grupos(list(fundidos.values()))


class ProvedorMLAmbas(Provedor):
    """Mercado Livre com TODAS as contas juntas — para o dia em que o mesmo
    motorista coleta as duas. Um Atualizar coleta as contas em sequencia e funde
    os grupos de mesmo SKU + quantidade (a separacao fisica vira POR PRODUTO,
    uma pilha so). A impressao baixa as etiquetas de cada conta com o token dela
    e junta tudo num ZIP unico; o estado de "ja impresso" continua POR CONTA
    (gravado no estado_grupos.json de cada uma)."""

    nome = "Mercado Livre (ambas)"
    suporta_identificacao = True
    suporta_contas = True
    organiza_envio = False

    def __init__(self) -> None:
        self._tokens_cred: dict[str, dict] = {}   # {conta: cred} (cache de token)
        self.contagem_dias = {}

    def contas(self) -> list[str]:
        return core.listar_contas()

    def definir_conta(self, nome: str) -> None:
        pass    # a GUI troca de PROVEDOR ao sair do modo Ambas, nao de conta

    def _token(self, conta: str) -> str:
        # definir_conta ANTES de tudo: se o obter_token precisar renovar, o
        # refresh_token rotacionado e salvo no credenciais.json DESTA conta.
        core.definir_conta(conta)
        cred = self._tokens_cred.get(conta)
        if cred is None:
            cred = self._tokens_cred[conta] = core.carregar_credenciais()
        return core.obter_token(cred)

    def coletar(self, *, dia=None, somente_hoje=True, progresso=None) -> list:
        por_conta: dict[str, list] = {}
        contagem: dict[str, int] = {}
        for conta in self.contas():
            token = self._token(conta)
            coleta = core.coletar_grupos(
                token, self._tokens_cred[conta]["seller_id"], dia=dia,
                somente_hoje=somente_hoje, progresso=progresso)
            por_conta[conta] = coleta.grupos
            for d, n in core.resumo_por_dia(getattr(coleta, "prontos", [])):
                d = "" if d == "(sem data)" else d
                contagem[d] = contagem.get(d, 0) + n
        self.contagem_dias = contagem
        return fundir_grupos(por_conta)

    # ---- estado composto: {conta: estado_da_conta} -------------------------
    def carregar_estado(self) -> dict:
        estados = {}
        for conta in self.contas():
            core.definir_conta(conta)
            estados[conta] = core.carregar_estado()
        return estados

    def envios_pendentes(self, estado: dict, grupo) -> list:
        pend = []
        for conta, sub in getattr(grupo, "por_conta", {}).items():
            pend.extend(core.envios_pendentes(estado.get(conta, {}), sub))
        return pend

    def status_grupo(self, estado: dict, grupo) -> str:
        pend = len(self.envios_pendentes(estado, grupo))
        if pend == 0:
            return "impresso"
        if pend == grupo.total_etiquetas:
            return "pendente"
        return "parcial"

    def marcar_impresso(self, estado: dict, grupo, ids: list) -> None:
        """Marca cada pedaco NO ESTADO DA PROPRIA CONTA (arquivo por conta)."""
        alvo = set(ids)
        for conta, sub in grupo.por_conta.items():
            proprios = [i for i in sub.shipment_ids if i in alvo]
            if not proprios:
                continue
            core.definir_conta(conta)   # aponta o estado_grupos.json da conta
            core.marcar_impresso(estado.setdefault(conta, {}), sub, proprios)

    # ---- impressao ----------------------------------------------------------
    def imprimir_lotes(self, grupos: list, estado: dict, *, modo="nenhuma") -> tuple:
        """UM ZIP com os pendentes de todos os grupos fundidos (etiquetas de
        cada conta baixadas com o token dela). Nada e marcado aqui — a GUI
        confirma e chama marcar_impresso. Como no ML normal, uma falha de
        download aborta tudo (nada e gerado nem marcado)."""
        nomes = core.carregar_nomes() if modo == "carimbo_nome" else None
        partes: list[str] = []
        pendentes: list[tuple] = []
        for g in grupos:
            zpl_g: list[str] = []
            pend_g: list = []
            for conta, sub in g.por_conta.items():
                pend_c = core.envios_pendentes(estado.get(conta, {}), sub)
                if not pend_c:
                    continue
                zpl = core.baixar_zpl(self._token(conta), pend_c)
                if "^XA" not in zpl:
                    raise core.SeparadorError("A API nao retornou ZPL valido (sem ^XA).")
                zpl_g.append(core._carimbar_grupo(zpl, g, modo, nomes))
                pend_g.extend(pend_c)
            if not pend_g:
                continue
            if modo == "divisoria":
                partes.append(core.zpl_divisoria(g))
            partes.extend(zpl_g)
            pendentes.append((g, pend_g))
        if pendentes:
            core._gerar_zip(f"AMBAS x{len(pendentes)}", "\n".join(partes))
        return pendentes, []

    def reimprimir(self, grupo) -> list:
        modo = core._modo_ident_efetivo()
        partes: list[str] = []
        ids: list = []
        for conta, sub in grupo.por_conta.items():
            if not sub.shipment_ids:
                continue
            zpl = core.baixar_zpl(self._token(conta), sub.shipment_ids)
            if "^XA" not in zpl:
                raise core.SeparadorError("A API nao retornou ZPL valido (sem ^XA).")
            partes.append(core._carimbar_grupo(zpl, grupo, modo))
            ids.extend(sub.shipment_ids)
        if ids:
            core.gerar_zip_etiquetas(grupo, "\n".join(partes))
        return ids


def criar_provedor(nome: str) -> Provedor:
    """Fabrica pelo rotulo do marketplace ('shopee' -> Shopee, senao ML)."""
    return ProvedorShopee() if (nome or "").strip().lower() == "shopee" else ProvedorML()
