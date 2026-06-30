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
    def imprimir_grupo(self, grupo, estado: dict, *, modo="nenhuma") -> list:
        raise NotImplementedError

    def imprimir_lotes(self, grupos: list, estado: dict, *, modo="nenhuma") -> tuple:
        """Imprime varios grupos. Devolve (impressos, falhas)."""
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

    def contas(self) -> list[str]:
        return core.listar_contas()

    def definir_conta(self, nome: str) -> None:
        core.definir_conta(nome)

    def _renovar(self) -> str:
        self.cred = core.carregar_credenciais()
        self.token = core.renovar_token(self.cred)
        return self.token

    def coletar(self, *, dia=None, somente_hoje=True, progresso=None) -> list:
        token = self._renovar()
        return core.coletar_grupos(
            token, self.cred["seller_id"], dia=dia,
            somente_hoje=somente_hoje, progresso=progresso,
        ).grupos

    def carregar_estado(self) -> dict:
        return core.carregar_estado()

    def marcar_impresso(self, estado: dict, grupo, ids: list) -> None:
        core.marcar_impresso(estado, grupo, ids)

    def imprimir_grupo(self, grupo, estado: dict, *, modo="nenhuma") -> list:
        token = self.token or self._renovar()
        return core.imprimir_pendentes(token, grupo, estado)

    def imprimir_lotes(self, grupos: list, estado: dict, *, modo="nenhuma") -> tuple:
        # (impressos, falhas) — o ML nao tem falha parcial, entao falhas=[].
        token = self.token or self._renovar()
        return core.gerar_zip_lotes(token, grupos, estado, modo=modo), []

    def reimprimir(self, grupo) -> list:
        token = self.token or self._renovar()
        return core.reimprimir(token, grupo)


class ProvedorShopee(Provedor):
    nome = "Shopee"
    suporta_identificacao = False
    suporta_contas = False
    organiza_envio = True

    def __init__(self) -> None:
        self.cred = None
        # Setup unico, so usado quando algum pedido exige (ver _montar_dropoff).
        self.branch_id = None
        self.sender_real_name = None

    def _creds(self) -> dict:
        if self.cred is None:
            self.cred = shopee.carregar_credenciais()
        return self.cred

    def coletar(self, *, dia=None, somente_hoje=True, progresso=None) -> list:
        grupos, _ = shopee.coletar_grupos(self._creds(), dia=dia, somente_hoje=somente_hoje)
        # Rastreio (AWB) dos grupos de 1 pedido ja impresso, para conferencia.
        shopee.preencher_rastreios(self._creds(), grupos, shopee.carregar_estado())
        return grupos

    def carregar_estado(self) -> dict:
        return shopee.carregar_estado()

    def marcar_impresso(self, estado: dict, grupo, ids: list) -> None:
        shopee.marcar_impresso(estado, grupo, ids)

    def imprimir_grupo(self, grupo, estado: dict, *, modo="nenhuma") -> list:
        return shopee.imprimir_grupo(
            self._creds(), grupo, estado,
            branch_id=self.branch_id, sender_real_name=self.sender_real_name,
        )

    def imprimir_lotes(self, grupos: list, estado: dict, *, modo="nenhuma") -> tuple:
        return shopee.imprimir_lotes(
            self._creds(), grupos, estado,
            branch_id=self.branch_id, sender_real_name=self.sender_real_name,
        )

    def reimprimir(self, grupo) -> list:
        return shopee.reimprimir_grupo(self._creds(), grupo)


def criar_provedor(nome: str) -> Provedor:
    """Fabrica pelo rotulo do marketplace ('shopee' -> Shopee, senao ML)."""
    return ProvedorShopee() if (nome or "").strip().lower() == "shopee" else ProvedorML()
