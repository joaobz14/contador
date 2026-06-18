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
from tkinter import messagebox, ttk

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
        self._build_ui()
        self.root.after(300, self.atualizar)  # carrega assim que abre

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        self.root.title("Separador de Etiquetas — Mercado Livre")
        self.root.geometry("580x700")
        self.root.minsize(460, 480)

        topo = ttk.Frame(self.root, padding=10)
        topo.pack(fill="x")
        self.btn_atualizar = ttk.Button(topo, text="🔄 Atualizar", command=self.atualizar)
        self.btn_atualizar.pack(side="left")
        self.btn_proximo = ttk.Button(topo, text="⏭ Próximo pendente",
                                       command=self.imprimir_proximo)
        self.btn_proximo.pack(side="left", padx=6)
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

    def _ocupar(self, ocupado: bool, msg: str = "") -> None:
        self.ocupado = ocupado
        estado = "disabled" if ocupado else "normal"
        self.btn_atualizar.config(state=estado)
        self.btn_proximo.config(state=estado)
        self.lbl_status.config(text=msg)

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
            coleta = core.coletar_grupos(
                self.token, self.cred["seller_id"], progresso=self._progresso
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

        total_et = sum(g.total_etiquetas for g in self.grupos)
        impressos = sum(1 for g in self.grupos
                        if core.status_grupo(self.estado, g) == "impresso")
        self.lbl_resumo.config(
            text=f"{len(self.grupos)} grupos · {total_et} etiquetas · {impressos} impressos")

        if not self.grupos:
            ttk.Label(self.lista, text="Nenhum grupo para imprimir hoje. 🎉",
                      padding=24).pack()
            self._ocupar(False, f"Atualizado às {datetime.now():%H:%M}")
            return

        por_qtd: dict[int, list] = {}
        for g in self.grupos:
            por_qtd.setdefault(g.quantidade, []).append(g)

        for qtd in sorted(por_qtd):
            ttk.Label(self.lista, text=f"  Quantidade por pedido = {qtd}",
                      font=("Segoe UI", 10, "bold")).pack(fill="x", pady=(12, 4))
            for g in por_qtd[qtd]:
                self._linha(g)

        self._ocupar(False, f"Atualizado às {datetime.now():%H:%M}")

    def _linha(self, g) -> None:
        impresso = core.status_grupo(self.estado, g) == "impresso"
        fr = ttk.Frame(self.lista, padding=(8, 6), relief="solid", borderwidth=1)
        fr.pack(fill="x", pady=2)

        esq = ttk.Frame(fr)
        esq.pack(side="left", fill="x", expand=True)
        ttk.Label(esq, text=g.nome, font=("Segoe UI", 9)).pack(anchor="w")
        ttk.Label(esq, text=f"{g.total_etiquetas} etiqueta(s)",
                  foreground=CINZA, font=("Segoe UI", 8)).pack(anchor="w")

        if impresso:
            ttk.Label(fr, text="✓ Impresso", foreground=VERDE,
                      font=("Segoe UI", 9, "bold")).pack(side="right")
        else:
            ttk.Button(fr, text="Imprimir",
                       command=lambda gg=g: self.imprimir(gg)).pack(side="right")

    # -------------------------------------------------------------- IMPRIMIR
    def imprimir(self, g) -> None:
        if self.ocupado:
            return
        self._ocupar(True, f"Imprimindo: {g.nome} ...")
        threading.Thread(target=self._imprimir_thread, args=(g,), daemon=True).start()

    def _imprimir_thread(self, g) -> None:
        try:
            zpl = core.baixar_zpl(self.token, g.shipment_ids)
            if "^XA" not in zpl:
                raise RuntimeError("A API não retornou ZPL válido para este grupo.")
            core.gerar_zip_etiquetas(g, zpl)
            core.marcar_impresso(self.estado, g)
        except Exception as e:
            self.root.after(0, lambda erro=e: self._erro(str(erro)))
            return
        self.root.after(0, self._render)

    def imprimir_proximo(self) -> None:
        pend = next((g for g in self.grupos
                     if core.status_grupo(self.estado, g) == "pendente"), None)
        if not pend:
            messagebox.showinfo("Tudo certo", "Nenhum grupo pendente. 🎉")
            return
        self.imprimir(pend)


if __name__ == "__main__":
    root = tk.Tk()
    SeparadorApp(root)
    root.mainloop()
