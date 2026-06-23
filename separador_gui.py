"""
separador_gui.py
Telinha do Separador de Etiquetas do Mercado Livre.
Mostra os grupos de hoje (SKU + quantidade) com um botao [Imprimir] em cada.
Reaproveita toda a logica de separador_etiquetas_ml.py (precisa estar na MESMA pasta).

Como usar:
  python separador_gui.py
(Quando estiver redondo, pode renomear para separador_gui.pyw para abrir sem a
janela preta do terminal.)
"""

import threading
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, simpledialog, ttk

import separador_etiquetas_ml as core

VERDE = "#0f6e56"
CINZA = "#6b7280"


class SeparadorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.token = None
        self.cred = None
        self.grupos: list = []
        self.estado: dict = {}
        self.ocupado = False
        self.config = core.aplicar_config()   # aplica conta_ativa + identificacao
        # Modo de identificacao do produto na impressao: carimbo | divisoria | nenhuma.
        self.modo_ident = self.config.get("modo_identificacao")
        if self.modo_ident is None:           # compatibilidade com o config antigo
            self.modo_ident = "carimbo" if self.config.get("carimbar_sku") else "nenhuma"
        core.CARIMBAR_SKU = (self.modo_ident == "carimbo")
        self._sel_vars: list = []             # (grupo, BooleanVar) das caixinhas
        self._verificar_migracao()            # migra conta antiga da raiz (1a vez)
        self._build_ui()
        self._tela_inicial()           # abre parado: usuario escolhe o filtro
        # Salva o tamanho/posicao da janela ao fechar, para reabrir igual.
        self.root.protocol("WM_DELETE_WINDOW", self._ao_fechar)

    def _ao_fechar(self) -> None:
        try:
            self.config["geometria"] = self.root.geometry()
            core.salvar_config(self.config)
        except Exception:
            pass
        self.root.destroy()

    def _verificar_migracao(self) -> None:
        """Garante que exista uma conta ativa válida apontada.

        Se ainda houver um credenciais.json na RAIZ (conta antiga), pergunta o
        nome e migra para contas/{nome}/ — mesmo que já existam outras contas
        (caso de quem adicionou a 2ª conta antes de migrar a 1ª). Também escolhe
        uma conta ativa padrão se a salva no config sumir/for inválida.
        """
        # 1) Conta antiga ainda na raiz: pedir nome e migrar para contas/{nome}/
        if (core.PASTA_SCRIPT / "credenciais.json").exists():
            nome = simpledialog.askstring(
                "Nome da conta antiga",
                "Encontrei uma conta ainda solta na pasta principal.\n\n"
                "Qual o nome dela? (ex.: Gastromaq)",
                initialvalue="Gastromaq", parent=self.root)
            nome = (nome or "Gastromaq").strip() or "Gastromaq"
            core.migrar_conta_legado(nome)
            self.config["conta_ativa"] = nome
            core.salvar_config(self.config)
        # 2) Garante que a conta ativa aponte para uma conta existente
        contas = core.listar_contas()
        ativa = self.config.get("conta_ativa", "")
        if contas and ativa not in contas:
            ativa = contas[0]
            self.config["conta_ativa"] = ativa
            core.salvar_config(self.config)
        if ativa:
            core.definir_conta(ativa)

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        self.root.title("Separador de Etiquetas — Mercado Livre")
        # Restaura o tamanho/posicao salvos (ou usa o padrao na 1a vez).
        self.root.geometry(self.config.get("geometria") or "580x700")
        self.root.minsize(460, 480)

        topo = ttk.Frame(self.root, padding=10)
        topo.pack(fill="x")
        self.btn_atualizar = ttk.Button(topo, text="🔄 Atualizar", command=self.atualizar)
        self.btn_atualizar.pack(side="left")
        self.btn_proximo = ttk.Button(topo, text="⏭ Próximo pendente",
                                       command=self.imprimir_proximo)
        self.btn_proximo.pack(side="left", padx=6)

        # Seletor de conta (mostrado apenas quando ha 2+ contas configuradas).
        self.conta_var = tk.StringVar(value=self.config.get("conta_ativa", ""))
        self._frame_contas = ttk.Frame(topo)
        self._radios_conta: list = []
        self._rebuild_conta_selector()

        # Seletor de dia de despacho: Hoje (padrao) ou Amanha.
        # So mudam a escolha; a busca so acontece quando o usuario clica em Atualizar.
        self.modo = tk.StringVar(value="hoje")
        seletor = ttk.Frame(topo)
        seletor.pack(side="left", padx=6)
        self.radios = [
            ttk.Radiobutton(seletor, text="Hoje", value="hoje", variable=self.modo),
            ttk.Radiobutton(seletor, text="Amanhã", value="amanha", variable=self.modo),
        ]
        for r in self.radios:
            r.pack(side="left", padx=(0, 6))

        # Modo de identificacao do produto na impressao (preferencia lembrada).
        self._ident_labels = {"carimbo": "Carimbo no DANFE",
                              "divisoria": "Etiqueta divisória", "nenhuma": "Nenhuma"}
        self._ident_valor = {v: k for k, v in self._ident_labels.items()}
        ttk.Label(topo, text="Identificação:").pack(side="left", padx=(8, 2))
        self.cb_ident = ttk.Combobox(topo, width=16, state="readonly",
                                     values=list(self._ident_labels.values()))
        self.cb_ident.set(self._ident_labels[self.modo_ident])
        self.cb_ident.bind("<<ComboboxSelected>>", self._trocar_identificacao)
        self.cb_ident.pack(side="left", padx=(0, 8))

        self.lbl_resumo = ttk.Label(topo, text="")
        self.lbl_resumo.pack(side="right")

        self.prog = ttk.Progressbar(self.root, mode="determinate")
        self.lbl_status = ttk.Label(self.root, text="", padding=(12, 0), foreground=CINZA)
        self.lbl_status.pack(fill="x")

        cont = ttk.Frame(self.root)
        cont.pack(fill="both", expand=True, padx=10, pady=(6, 10))
        self.canvas = tk.Canvas(cont, highlightthickness=0)
        sb = ttk.Scrollbar(cont, orient="vertical", command=self.canvas.yview)
        self.lista = ttk.Frame(self.canvas)
        self.lista.bind("<Configure>",
                        lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self._janela = self.canvas.create_window((0, 0), window=self.lista, anchor="nw")
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfig(self._janela, width=e.width))
        self.canvas.configure(yscrollcommand=sb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.canvas.bind_all("<MouseWheel>",
                             lambda e: self.canvas.yview_scroll(int(-e.delta / 120), "units"))

    def _rebuild_conta_selector(self) -> None:
        """Reconstroi os radio buttons de conta. Exibe so com 2+ contas."""
        for w in self._frame_contas.winfo_children():
            w.destroy()
        self._radios_conta.clear()
        contas = core.listar_contas()
        if len(contas) < 2:
            self._frame_contas.pack_forget()
            return
        self._frame_contas.pack(side="left", padx=(0, 6))
        for nome in contas:
            r = ttk.Radiobutton(self._frame_contas, text=nome, value=nome,
                                variable=self.conta_var,
                                command=lambda n=nome: self._trocar_conta(n))
            r.pack(side="left", padx=(0, 4))
            self._radios_conta.append(r)

    def _trocar_conta(self, nome: str) -> None:
        """Troca a conta ativa e volta para a tela inicial (sem buscar).
        A busca so acontece quando o usuario escolhe o dia e clica em Atualizar."""
        core.definir_conta(nome)
        self.config["conta_ativa"] = nome
        core.salvar_config(self.config)
        self._tela_inicial()

    def _ocupar(self, ocupado: bool, msg: str = "") -> None:
        self.ocupado = ocupado
        estado = "disabled" if ocupado else "normal"
        self.btn_atualizar.config(state=estado)
        self.btn_proximo.config(state=estado)
        self.cb_ident.config(state="disabled" if ocupado else "readonly")
        for r in self.radios:
            r.config(state=estado)
        for r in self._radios_conta:
            r.config(state=estado)
        self.lbl_status.config(text=msg)

    def _trocar_identificacao(self, event=None) -> None:
        """Troca o modo de identificacao (carimbo/divisoria/nenhuma) e lembra."""
        self.modo_ident = self._ident_valor.get(self.cb_ident.get(), "nenhuma")
        core.CARIMBAR_SKU = (self.modo_ident == "carimbo")
        self.config["modo_identificacao"] = self.modo_ident
        core.salvar_config(self.config)

    def _tela_inicial(self) -> None:
        """Tela de abertura: nada e buscado ate o usuario escolher e clicar."""
        for w in self.lista.winfo_children():
            w.destroy()
        self.lbl_resumo.config(text="")
        tem_contas = len(core.listar_contas()) >= 2
        prefixo = "Escolha a conta e o dia" if tem_contas else "Escolha o dia (Hoje ou Amanhã)"
        ttk.Label(
            self.lista, padding=24, justify="center", foreground=CINZA,
            text=(f"{prefixo} e clique em 🔄 Atualizar\npara buscar os pedidos."),
        ).pack()
        self.lbl_status.config(text="Pronto. Aguardando você escolher o filtro.")

    # ------------------------------------------------------------ ATUALIZAR
    def atualizar(self) -> None:
        if self.ocupado:
            return
        self._ocupar(True, "Carregando pedidos...")
        self.prog.pack(fill="x", padx=12, pady=(0, 4))
        self.prog.config(value=0)
        threading.Thread(target=self._atualizar_thread, daemon=True).start()

    def _progresso(self, feitos: int, total: int) -> None:
        def upd():
            self.prog.config(maximum=total, value=feitos)
            self.lbl_status.config(text=f"Verificando envios: {feitos}/{total}")
        self.root.after(0, upd)

    def _atualizar_thread(self) -> None:
        try:
            self.cred = core.carregar_credenciais()
            self.token = core.renovar_token(self.cred)
            dia = core._amanha_br() if self.modo.get() == "amanha" else None
            coleta = core.coletar_grupos(
                self.token, self.cred["seller_id"], dia=dia, progresso=self._progresso
            )
            grupos = coleta.grupos
        except Exception as e:
            self.root.after(0, lambda erro=e: self._erro(str(erro)))
            return
        self.grupos = grupos
        self.estado = core.carregar_estado()
        self.root.after(0, self._render)

    def _erro(self, msg: str) -> None:
        self.prog.pack_forget()
        self._ocupar(False, "")
        messagebox.showerror("Erro", msg)

    # --------------------------------------------------------------- RENDER
    def _render(self) -> None:
        self.prog.pack_forget()
        for w in self.lista.winfo_children():
            w.destroy()
        self._sel_vars = []          # caixinhas sao recriadas a cada render

        # Separa quem falta imprimir (topo) de quem ja foi impresso (arquivadas),
        # para que um grupo pendente nunca fique "perdido" no meio dos ✓ verdes.
        estados = [(g, core.status_grupo(self.estado, g)) for g in self.grupos]
        pendentes = [g for g, s in estados if s != "impresso"]
        arquivadas = [g for g, s in estados if s == "impresso"]

        total_et = sum(g.total_etiquetas for g in self.grupos)
        self.lbl_resumo.config(
            text=f"{len(self.grupos)} grupos · {total_et} etiquetas · "
                 f"{len(arquivadas)} impressos")

        dia_txt = "amanhã" if self.modo.get() == "amanha" else "hoje"
        if not self.grupos:
            ttk.Label(self.lista, text=f"Nenhum grupo para imprimir {dia_txt}. 🎉",
                      padding=24).pack()
            self._ocupar(False, f"Atualizado às {datetime.now():%H:%M}")
            return

        # ----- Seção: para imprimir (pendentes/parciais), agrupado por quantidade
        if pendentes:
            cab = ttk.Frame(self.lista)
            cab.pack(fill="x", pady=(8, 2))
            ttk.Label(cab, text="🖨  Para imprimir",
                      font=("Segoe UI", 11, "bold")).pack(side="left")
            ttk.Button(cab, text="🖨 Imprimir selecionados",
                       command=self.imprimir_lotes).pack(side="right")
            por_qtd: dict[int, list] = {}
            for g in pendentes:
                por_qtd.setdefault(g.quantidade, []).append(g)
            for qtd in sorted(por_qtd):
                ttk.Label(self.lista, text=f"  Quantidade por pedido = {qtd}",
                          font=("Segoe UI", 10, "bold")).pack(fill="x", pady=(8, 4))
                for g in por_qtd[qtd]:
                    self._linha(g, selecionavel=True)
        else:
            ttk.Label(self.lista, text=f"Tudo impresso {dia_txt}! 🎉",
                      padding=(0, 12)).pack()

        # ----- Seção: já impressas (arquivadas), embaixo e separadas
        if arquivadas:
            ttk.Label(self.lista,
                      text=f"✓  Já impressas — arquivadas ({len(arquivadas)})",
                      font=("Segoe UI", 11, "bold"), foreground=CINZA
                      ).pack(fill="x", pady=(16, 2))
            for g in arquivadas:
                self._linha(g)

        self._ocupar(False, f"Atualizado às {datetime.now():%H:%M}")

    def _linha(self, g, selecionavel: bool = False) -> None:
        status = core.status_grupo(self.estado, g)
        faltam = len(core.envios_pendentes(self.estado, g))
        fr = ttk.Frame(self.lista, padding=(8, 6), relief="solid", borderwidth=1)
        fr.pack(fill="x", pady=2)

        if selecionavel:                       # caixinha para "Imprimir selecionados"
            var = tk.BooleanVar(value=False)
            ttk.Checkbutton(fr, variable=var).pack(side="left", padx=(0, 6))
            self._sel_vars.append((g, var))

        esq = ttk.Frame(fr)
        esq.pack(side="left", fill="x", expand=True)
        ttk.Label(esq, text=g.nome, font=("Segoe UI", 9)).pack(anchor="w")
        if status == "parcial":
            sub = (f"{g.total_etiquetas - faltam} de {g.total_etiquetas} impressas "
                   f"· faltam {faltam}")
        else:
            sub = f"{g.total_etiquetas} etiqueta(s)"
        ttk.Label(esq, text=sub, foreground=CINZA, font=("Segoe UI", 8)).pack(anchor="w")

        # Reimprimir: refaz as etiquetas do grupo sem mexer no controle de impresso.
        ttk.Button(fr, text="↻ Reimprimir",
                   command=lambda gg=g: self.reimprimir(gg)).pack(side="right", padx=(6, 0))

        if status == "impresso":
            ttk.Label(fr, text="✓ Impresso", foreground=VERDE,
                      font=("Segoe UI", 9, "bold")).pack(side="right")
        else:
            texto = "Imprimir faltantes" if status == "parcial" else "Imprimir"
            ttk.Button(fr, text=texto,
                       command=lambda gg=g: self.imprimir(gg)).pack(side="right")

    # -------------------------------------------------------------- IMPRIMIR
    def imprimir(self, g) -> None:
        if self.ocupado:
            return
        self._ocupar(True, f"Imprimindo: {g.nome} ...")
        threading.Thread(target=self._imprimir_thread, args=(g,), daemon=True).start()

    def _imprimir_thread(self, g) -> None:
        try:
            core.imprimir_pendentes(self.token, g, self.estado)
        except Exception as e:
            self.root.after(0, lambda erro=e: self._erro(str(erro)))
            return
        self.root.after(0, self._render)

    def reimprimir(self, g) -> None:
        if self.ocupado:
            return
        if not messagebox.askyesno(
                "Reimprimir",
                f"Reimprimir TODAS as {g.total_etiquetas} etiqueta(s) de:\n\n{g.nome}"
                f" (qtd {g.quantidade})?\n\nO controle de impresso não muda."):
            return
        self._ocupar(True, f"Reimprimindo: {g.nome} ...")
        threading.Thread(target=self._reimprimir_thread, args=(g,), daemon=True).start()

    def _reimprimir_thread(self, g) -> None:
        try:
            core.reimprimir(self.token, g)
        except Exception as e:
            self.root.after(0, lambda erro=e: self._erro(str(erro)))
            return
        self.root.after(0, self._render)

    # ------------------------------------------------------- IMPRIMIR LOTES
    def imprimir_lotes(self) -> None:
        if self.ocupado:
            return
        selecionados = [g for g, v in self._sel_vars if v.get()]
        if not selecionados:
            messagebox.showinfo("Imprimir lotes",
                                "Marque ao menos um lote na caixinha à esquerda.")
            return
        modo_txt = self._ident_labels.get(self.modo_ident, "")
        self._ocupar(True, f"Imprimindo {len(selecionados)} lote(s) ({modo_txt}) ...")
        threading.Thread(target=self._imprimir_lotes_thread,
                         args=(selecionados,), daemon=True).start()

    def _imprimir_lotes_thread(self, grupos) -> None:
        try:
            impressos = core.gerar_zip_lotes(self.token, grupos, self.estado,
                                             modo=self.modo_ident)
        except Exception as e:
            self.root.after(0, lambda erro=e: self._erro(str(erro)))
            return
        self.root.after(0, lambda: self._pos_lotes(impressos))

    def _pos_lotes(self, impressos: list) -> None:
        self._ocupar(False, "")
        if not impressos:
            messagebox.showinfo("Imprimir lotes",
                                "Nada pendente nos lotes selecionados.")
            return
        n = len(impressos)
        marcar = True
        if n >= 2:                              # confirma o resultado fisico da impressao
            marcar = messagebox.askyesno(
                "Confirmar impressão",
                f"Enviei {n} lote(s) para a impressora.\n\n"
                "As etiquetas saíram corretamente?\n\n"
                "Sim = marca como impressos.\n"
                "Não = mantém pendentes para reimprimir.")
        if marcar:
            for g, pend in impressos:
                core.marcar_impresso(self.estado, g, pend)
        self._render()

    def imprimir_proximo(self) -> None:
        pend = next((g for g in self.grupos
                     if core.status_grupo(self.estado, g) == "pendente"), None)
        if not pend:
            messagebox.showinfo("Tudo certo", "Nenhum grupo pendente. 🎉")
            return
        self.imprimir(pend)


def main() -> None:
    root = tk.Tk()
    SeparadorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
