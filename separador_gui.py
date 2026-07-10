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

import provedores
import separador_etiquetas_ml as core
from registro import log, sem_segredos

VERDE = "#0f6e56"
CINZA = "#6b7280"


class SeparadorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.grupos: list = []
        self.estado: dict = {}
        self.ocupado = False
        self.config = core.aplicar_config()   # aplica conta_ativa + identificacao
        # Modo de identificacao do produto na impressao: carimbo | divisoria | nenhuma.
        self.modo_ident = self.config.get("modo_identificacao")
        if self.modo_ident is None:           # compatibilidade com o config antigo
            self.modo_ident = "carimbo" if self.config.get("carimbar_sku") else "nenhuma"
        core.MODO_IDENT = self.modo_ident
        core.CARIMBAR_SKU = (self.modo_ident == "carimbo")
        self._sel_vars: list = []             # (grupo, BooleanVar) das caixinhas
        self._blocos: list = []               # (master_var, [vars]) por bloco de qtd
        self._sel_antes: set = set()          # selecao preservada entre re-renders
        self._sel_arq: list = []              # (grupo, BooleanVar) das arquivadas
        self._verificar_migracao()            # migra conta antiga da raiz (1a vez)
        # Marketplace ativo (Mercado Livre / Shopee) e seu provedor.
        self.marketplace = self.config.get("marketplace", "Mercado Livre")
        self.prov = provedores.criar_provedor(self.marketplace)
        self._aplicar_conta_no_provedor()
        self._build_ui()
        self._tela_inicial()           # abre parado: usuario escolhe o filtro
        # Salva o tamanho/posicao da janela ao fechar, para reabrir igual.
        self.root.protocol("WM_DELETE_WINDOW", self._ao_fechar)
        log.info("Separador iniciado (%s)", self._ctx_log())

    def _ctx_log(self) -> str:
        """Contexto para o log operacional (loja e, no ML, a conta ativa). Le so
        dados simples (dict/provedor) — seguro de chamar de threads de fundo. O
        nome do provedor ja distingue ML / Shopee / 'Mercado Livre (ambas)'."""
        conta = self.config.get("conta_ativa", "")
        if self.prov.suporta_contas and conta and "ambas" not in self.prov.nome.lower():
            return f"loja={self.prov.nome} conta={conta}"
        return f"loja={self.prov.nome}"

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

    def _aplicar_conta_no_provedor(self) -> None:
        """Para provedores com sub-contas (ML), aponta para a conta salva (ou a 1a)."""
        if not self.prov.suporta_contas:
            return
        contas = self.prov.contas()
        ativa = self.config.get("conta_ativa", "")
        if contas:
            self.prov.definir_conta(ativa if ativa in contas else contas[0])

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        self.root.title("Separador de Etiquetas")
        # Restaura o tamanho/posicao salvos (ou usa o padrao na 1a vez).
        self.root.geometry(self.config.get("geometria") or "580x700")
        self.root.minsize(460, 480)

        # Linha de marketplace (loja): Mercado Livre / Shopee.
        topo_mkt = ttk.Frame(self.root, padding=(10, 8, 10, 0))
        topo_mkt.pack(fill="x")
        ttk.Label(topo_mkt, text="Loja:").pack(side="left", padx=(0, 6))
        self.marketplace_var = tk.StringVar(value=self.marketplace)
        self._radios_mkt: list = []
        for nome in ("Mercado Livre", "Shopee"):
            r = ttk.Radiobutton(topo_mkt, text=nome, value=nome,
                                variable=self.marketplace_var,
                                command=lambda n=nome: self._trocar_marketplace(n))
            r.pack(side="left", padx=(0, 8))
            self._radios_mkt.append(r)
        # Editor de nomes amigaveis (SKU -> nome), a direita da linha da loja.
        ttk.Button(topo_mkt, text="✏ Nomes",
                   command=self.abrir_editor_nomes).pack(side="right")

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

        # Modo de identificacao do produto na impressao (preferencia lembrada).
        self._ident_labels = {"carimbo": "Carimbo SKU no DANFE",
                              "carimbo_nome": "Carimbo nome no DANFE",
                              "divisoria": "Etiqueta divisória", "nenhuma": "Nenhuma"}
        self._ident_valor = {v: k for k, v in self._ident_labels.items()}
        self.lbl_ident = ttk.Label(topo, text="Identificação:")
        self.lbl_ident.pack(side="left", padx=(8, 2))
        self.cb_ident = ttk.Combobox(topo, width=20, state="readonly",
                                     values=list(self._ident_labels.values()))
        self.cb_ident.set(self._ident_labels[self.modo_ident])
        self.cb_ident.bind("<<ComboboxSelected>>", self._trocar_identificacao)
        self.cb_ident.pack(side="left", padx=(0, 8))

        self.lbl_resumo = ttk.Label(topo, text="")
        self.lbl_resumo.pack(side="right")
        self._atualizar_visibilidade_topo()   # esconde conta/identificacao p/ Shopee

        # Seletor de dia de despacho, em linha propria (5 dias uteis nao cabem na
        # barra de cima). Mostra os proximos dias UTEIS (seg-sex); apos um
        # Atualizar, cada dia ganha a contagem de pedidos e datas FORA de seg-sex
        # com pedidos (fim de semana/atrasadas/sem data) aparecem numa linha
        # "Outras datas" — nenhum pedido fica invisivel. So muda a escolha; a
        # busca so acontece ao clicar em Atualizar.
        self._dias_uteis = core.proximos_dias_uteis()
        self.dia_sel = tk.StringVar(value=self._dias_uteis[0])
        self.linha_dia = ttk.Frame(self.root, padding=(10, 0, 10, 2))
        self.linha_dia.pack(fill="x")
        self.linha_outras = ttk.Frame(self.root, padding=(10, 0, 10, 6))
        self.radios = []
        self._rebuild_dias()

        self.prog = ttk.Progressbar(self.root, mode="determinate")
        self.lbl_status = ttk.Label(self.root, text="", padding=(12, 0), foreground=CINZA)
        self.lbl_status.pack(fill="x")

        # Master do "Marcar todos" (os pendentes visiveis). Recriado a cada render.
        self._sel_todos = tk.BooleanVar(value=False)

        # Busca na lista do dia (filtra por nome/SKU, sem rede). Linha propria,
        # mostrada so quando ha grupos carregados (ver _render/_tela_inicial).
        self.busca_var = tk.StringVar()
        self.busca_var.trace_add("write", lambda *_: self._on_busca())
        self.linha_busca = ttk.Frame(self.root, padding=(10, 0, 10, 4))
        ttk.Label(self.linha_busca, text="🔎 Buscar:").pack(side="left", padx=(0, 6))
        self.ent_busca = ttk.Entry(self.linha_busca, textvariable=self.busca_var)
        self.ent_busca.pack(side="left", fill="x", expand=True)

        # Rodape FIXO com "Imprimir selecionados" — sempre visivel, nao rola com a
        # lista. Aparece so quando ha grupos para imprimir (mostrado em _render).
        self.rodape = ttk.Frame(self.root, padding=(10, 6))
        self.btn_lotes = ttk.Button(self.rodape, text="🖨 Imprimir selecionados",
                                    command=self.imprimir_lotes, state="disabled")
        self.btn_lotes.pack(side="right")

        self.cont = ttk.Frame(self.root)
        self.cont.pack(fill="both", expand=True, padx=10, pady=(6, 10))
        self.canvas = tk.Canvas(self.cont, highlightthickness=0)
        sb = ttk.Scrollbar(self.cont, orient="vertical", command=self.canvas.yview)
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

        # Atalhos de teclado: F5 atualiza, Ctrl+F foca a busca, Esc limpa a busca.
        self.root.bind("<F5>", lambda e: self.atualizar())
        self.root.bind("<Control-f>", lambda e: self.ent_busca.focus_set())
        self.root.bind("<Escape>",
                       lambda e: self.busca_var.set("") if self.busca_var.get() else None)

    def _rebuild_dias(self, contagem: dict | None = None) -> None:
        """Reconstroi o seletor de dia de despacho.

        Sem `contagem` (antes do 1º Atualizar / troca de loja): so os proximos
        dias uteis. Com `contagem` ({data: n pedidos}, vinda da mesma busca):
        cada dia util mostra o total, e datas fora de seg-sex com pedidos
        (fim de semana, atrasadas ou sem data) entram na linha "Outras datas"."""
        contagem = contagem or {}
        self._dias_uteis = core.proximos_dias_uteis()   # recalcula (virada de dia)
        for w in self.linha_dia.winfo_children():
            w.destroy()
        for w in self.linha_outras.winfo_children():
            w.destroy()
        self.radios = []
        hoje_iso = core._hoje_br()

        def _radio(parent, iso: str, rotulo: str) -> None:
            r = ttk.Radiobutton(parent, text=rotulo, value=iso, variable=self.dia_sel)
            r.pack(side="left", padx=(0, 8))
            self.radios.append(r)

        ttk.Label(self.linha_dia, text="Dia de despacho:").pack(side="left", padx=(0, 8))
        for iso in self._dias_uteis:
            rotulo = core.rotulo_dia(iso) + (" (hoje)" if iso == hoje_iso else "")
            if contagem:
                rotulo += f" · {contagem.get(iso, 0)}"
            _radio(self.linha_dia, iso, rotulo)

        extras = sorted(d for d in contagem if d and d not in self._dias_uteis)
        sem_data = contagem.get("", 0)
        if extras or sem_data:
            ttk.Label(self.linha_outras, text="Outras datas:").pack(side="left", padx=(0, 8))
            for iso in extras:
                _radio(self.linha_outras, iso, f"{core.rotulo_dia(iso)} · {contagem[iso]}")
            if sem_data:
                _radio(self.linha_outras, "", f"Sem data · {sem_data}")
            self.linha_outras.pack(fill="x", after=self.linha_dia)
        else:
            self.linha_outras.pack_forget()

        # Selecao que deixou de existir (ex.: data extra que sumiu) volta pro 1º dia.
        validos = set(self._dias_uteis) | set(extras) | ({""} if sem_data else set())
        if self.dia_sel.get() not in validos:
            self.dia_sel.set(self._dias_uteis[0])

    def _rebuild_conta_selector(self) -> None:
        """Reconstroi os radios de conta. So aparece no ML com 2+ contas."""
        for w in self._frame_contas.winfo_children():
            w.destroy()
        self._radios_conta.clear()
        contas = self.prov.contas() if self.prov.suporta_contas else []
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
        # Modo "Ambas": junta as contas num dia de motorista unico (a separacao
        # fisica vira por produto). Escolha pontual — nao fica lembrada.
        r = ttk.Radiobutton(self._frame_contas, text="🌐 Ambas",
                            value=provedores.CONTA_AMBAS, variable=self.conta_var,
                            command=lambda: self._trocar_conta(provedores.CONTA_AMBAS))
        r.pack(side="left", padx=(0, 4))
        self._radios_conta.append(r)

    def _atualizar_visibilidade_topo(self) -> None:
        """Mostra/esconde a Identificação conforme o provedor (Shopee não carimba).
        O seletor de conta é refeito à parte (_rebuild_conta_selector)."""
        if self.prov.suporta_identificacao:
            self.lbl_ident.pack(side="left", padx=(8, 2))
            self.cb_ident.pack(side="left", padx=(0, 8))
        else:
            self.lbl_ident.pack_forget()
            self.cb_ident.pack_forget()

    def _trocar_marketplace(self, nome: str) -> None:
        """Troca o marketplace (ML/Shopee), recria o provedor e a tela inicial."""
        if self.ocupado:
            self.marketplace_var.set(self.marketplace)   # ignora troca durante busca
            return
        self.marketplace = nome
        self.prov = provedores.criar_provedor(nome)
        self._aplicar_conta_no_provedor()
        # Se estava no modo Ambas, o radio volta a refletir a conta salva
        # (o provedor novo e o normal da conta).
        if self.conta_var.get() == provedores.CONTA_AMBAS:
            self.conta_var.set(self.config.get("conta_ativa", ""))
        self.config["marketplace"] = nome
        core.salvar_config(self.config)
        self._rebuild_conta_selector()
        self._atualizar_visibilidade_topo()
        self.grupos = []
        self._tela_inicial()

    def _trocar_conta(self, nome: str) -> None:
        """Troca a conta ativa (ML) e volta para a tela inicial (sem buscar).
        A busca só acontece quando o usuário escolhe o dia e clica em Atualizar.

        "🌐 Ambas" troca o PROVEDOR (ProvedorMLAmbas: contas fundidas) e não é
        persistido — na próxima abertura o app volta à última conta normal."""
        if nome == provedores.CONTA_AMBAS:
            self.prov = provedores.ProvedorMLAmbas()
        else:
            if isinstance(self.prov, provedores.ProvedorMLAmbas):
                self.prov = provedores.criar_provedor(self.marketplace)
            self.prov.definir_conta(nome)
            self.config["conta_ativa"] = nome
            core.salvar_config(self.config)
        self.grupos = []
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
        for r in self._radios_mkt:
            r.config(state=estado)
        self._atualizar_contagem()          # reavalia o botao do rodape
        self.lbl_status.config(text=msg)

    def _mostrar_rodape(self, mostrar: bool) -> None:
        """Mostra/esconde o rodape fixo do 'Imprimir selecionados' (fica sobre a
        lista, antes do canvas, para nao rolar junto)."""
        if mostrar:
            self.rodape.pack(side="bottom", fill="x", before=self.cont)
        else:
            self.rodape.pack_forget()

    def _atualizar_contagem(self) -> None:
        """Atualiza o texto/estado do botao 'Imprimir selecionados' conforme as
        caixinhas marcadas. Chamado a cada clique numa caixinha."""
        self._sincronizar_selecao()         # mantem os 'marcar todos' coerentes
        n = sum(1 for _g, v in self._sel_vars if v.get())
        sufixo = f" ({n})" if n else ""
        self.btn_lotes.config(text=f"🖨 Imprimir selecionados{sufixo}",
                              state=("normal" if (n and not self.ocupado) else "disabled"))

    def _sincronizar_selecao(self) -> None:
        """Deixa os checkboxes 'marcar todos' (geral e por bloco) refletindo o
        estado real das caixinhas individuais (marcado = todas marcadas)."""
        for master, vars_ in self._blocos:
            master.set(bool(vars_) and all(v.get() for v in vars_))
        self._sel_todos.set(bool(self._sel_vars) and all(v.get() for _g, v in self._sel_vars))

    def _marcar_todos(self) -> None:
        """Marca/desmarca TODOS os pendentes visiveis de uma vez."""
        val = self._sel_todos.get()
        for _g, v in self._sel_vars:
            v.set(val)
        self._atualizar_contagem()

    def _marcar_bloco(self, master, vars_) -> None:
        """Marca/desmarca todos os grupos de um bloco de quantidade."""
        val = master.get()
        for v in vars_:
            v.set(val)
        self._atualizar_contagem()

    def _casa(self, g, termo: str) -> bool:
        """True se o grupo casa com o termo de busca (nome, SKU/chave ou itens do
        combo). Termo vazio casa com tudo."""
        if not termo:
            return True
        if termo in g.nome.lower() or termo in str(g.chave).lower():
            return True
        return any(termo in str(sku).lower() for sku, _ in getattr(g, "componentes", []))

    def _mostrar_busca(self, mostrar: bool) -> None:
        if mostrar:
            self.linha_busca.pack(fill="x", before=self.cont)
        else:
            self.linha_busca.pack_forget()

    def _on_busca(self) -> None:
        """Re-renderiza a lista aplicando o filtro (usa os grupos ja em memoria,
        sem rede)."""
        if self.grupos and not self.ocupado:
            self._render()

    def _trocar_identificacao(self, event=None) -> None:
        """Troca o modo de identificacao (carimbo/divisoria/nenhuma) e lembra."""
        self.modo_ident = self._ident_valor.get(self.cb_ident.get(), "nenhuma")
        core.MODO_IDENT = self.modo_ident
        core.CARIMBAR_SKU = (self.modo_ident == "carimbo")
        self.config["modo_identificacao"] = self.modo_ident
        core.salvar_config(self.config)

    def _tela_inicial(self) -> None:
        """Tela de abertura: nada e buscado ate o usuario escolher e clicar."""
        for w in self.lista.winfo_children():
            w.destroy()
        self._sel_vars = []
        self._blocos = []
        self._sel_arq = []
        self._mostrar_rodape(False)
        self._mostrar_busca(False)
        self._rebuild_dias()               # contagens antigas nao valem p/ loja nova
        self.root.title("Separador de Etiquetas")
        self.lbl_resumo.config(text="")
        tem_contas = self.prov.suporta_contas and len(self.prov.contas()) >= 2
        prefixo = "Escolha a conta e o dia" if tem_contas else "Escolha o dia da semana"
        ttk.Label(
            self.lista, padding=24, justify="center", foreground=CINZA,
            text=(f"{prefixo} e clique em 🔄 Atualizar\npara buscar os pedidos."),
        ).pack()
        self.lbl_status.config(text="Pronto. Aguardando você escolher o filtro.")

    # ------------------------------------------------------------ ATUALIZAR
    def atualizar(self) -> None:
        if self.ocupado:
            return
        # Dados novos (dia/conta/loja podem mudar): selecao antiga nao vale mais.
        self._sel_vars = []
        self._sel_antes = set()
        # Limpa a busca para um filtro antigo nao esconder os pedidos do novo dia.
        if self.busca_var.get():
            self.busca_var.set("")
        self._ocupar(True, "Carregando pedidos...")
        self.prog.pack(fill="x", padx=12, pady=(0, 4))
        self.prog.config(value=0)
        # Le a variavel Tkinter AQUI (thread principal) e passa o valor pronto:
        # widgets/StringVar nao devem ser tocados pela thread de fundo.
        dia = self.dia_sel.get()
        threading.Thread(target=self._atualizar_thread, args=(dia,), daemon=True).start()

    def _progresso(self, feitos: int, total: int) -> None:
        def upd():
            self.prog.config(maximum=total, value=feitos)
            self.lbl_status.config(text=f"Verificando envios: {feitos}/{total}")
        self.root.after(0, upd)

    def _atualizar_thread(self, dia: str) -> None:
        try:
            grupos = self.prov.coletar(dia=dia, somente_hoje=False,
                                       progresso=self._progresso)
            estado = self.prov.carregar_estado()
        except Exception as e:
            self.root.after(0, lambda erro=e: self._erro(str(erro)))
            return
        self.grupos = grupos
        self.estado = estado
        etiquetas = sum(g.total_etiquetas for g in grupos)
        log.info("Atualizar: %s dia=%s -> %d grupo(s), %d etiqueta(s)",
                 self._ctx_log(), dia or "(sem data)", len(grupos), etiquetas)
        self.root.after(0, self._render)

    def _erro(self, msg: str) -> None:
        # Ponto unico de erro da GUI: loga TODA falha ja com segredos redigidos
        # (a mensagem pode ser um HTTPError com a URL assinada da Shopee).
        log.error("Erro: %s", sem_segredos(msg))
        self.prog.pack_forget()
        self._ocupar(False, "")
        messagebox.showerror("Erro", msg)

    # --------------------------------------------------------------- RENDER
    def _render(self) -> None:
        self.prog.pack_forget()
        # Preserva o que estava marcado: um re-render (ex.: digitar na busca) nao
        # pode perder a selecao ja feita. Merge (nao recomputa): grupos escondidos
        # pelo filtro mantem a marcacao; desmarcar um visivel remove. Zerado em
        # atualizar() (dados novos).
        for g, v in self._sel_vars:
            chave = (g.chave, g.quantidade)
            (self._sel_antes.add if v.get() else self._sel_antes.discard)(chave)
        for w in self.lista.winfo_children():
            w.destroy()
        self._sel_vars = []          # caixinhas sao recriadas a cada render
        self._blocos = []
        self._sel_arq = []

        dia = self.dia_sel.get()
        dia_txt = core.rotulo_dia(dia) if dia else "sem data"
        # Seletor de dias ganha a contagem por dia (e datas extras) da coleta.
        self._rebuild_dias(getattr(self.prov, "contagem_dias", {}))
        # Busca aparece assim que ha grupos carregados (filtra sem rede).
        self._mostrar_busca(bool(self.grupos))
        termo = self.busca_var.get().strip().lower()
        grupos = [g for g in self.grupos if self._casa(g, termo)]

        # Separa quem falta imprimir (topo) de quem ja foi impresso (arquivadas),
        # para que um grupo pendente nunca fique "perdido" no meio dos ✓ verdes.
        estados = [(g, self.prov.status_grupo(self.estado, g)) for g in grupos]
        pendentes = [g for g, s in estados if s != "impresso"]
        arquivadas = [g for g, s in estados if s == "impresso"]

        total_et = sum(g.total_etiquetas for g in grupos)
        prefixo = "🔎 " if termo else ""
        self.lbl_resumo.config(
            text=f"{prefixo}{len(grupos)} grupos · {total_et} etiquetas · "
                 f"{len(arquivadas)} impressos")

        # Titulo da janela com os pendentes do dia (independe do filtro da busca).
        pend_total = sum(1 for g in self.grupos
                         if self.prov.status_grupo(self.estado, g) != "impresso")
        self.root.title(f"Separador de Etiquetas — {pend_total} pendente(s) · {dia_txt}")

        # Rodape do "Imprimir selecionados" aparece so quando ha grupos pendentes.
        self._mostrar_rodape(bool(pendentes))

        if not self.grupos:
            ttk.Label(self.lista, text=f"Nenhum grupo para imprimir em {dia_txt}. 🎉",
                      padding=24).pack()
            self._ocupar(False, f"Atualizado às {datetime.now():%H:%M}")
            return
        if not grupos:                       # ha grupos, mas nenhum casa com a busca
            ttk.Label(self.lista, padding=24, foreground=CINZA,
                      text=f"Nenhum grupo casa com “{termo}”.").pack()
            self._ocupar(False, f"Atualizado às {datetime.now():%H:%M}")
            return

        # ----- Seção: para imprimir (pendentes/parciais), agrupado por quantidade
        if pendentes:
            cab = ttk.Frame(self.lista)
            cab.pack(fill="x", pady=(8, 2))
            ttk.Label(cab, text="🖨  Para imprimir",
                      font=("Segoe UI", 11, "bold")).pack(side="left")
            ttk.Checkbutton(cab, text="Marcar todos", variable=self._sel_todos,
                            command=self._marcar_todos).pack(side="right")
            por_qtd: dict[int, list] = {}
            for g in pendentes:
                por_qtd.setdefault(g.quantidade, []).append(g)
            for qtd in sorted(por_qtd):
                bloco_master = tk.BooleanVar(value=False)
                bloco_vars: list = []
                ttk.Checkbutton(
                    self.lista, text=f"Quantidade por pedido = {qtd}",
                    variable=bloco_master,
                    command=lambda bv=bloco_vars, m=bloco_master: self._marcar_bloco(m, bv),
                ).pack(fill="x", pady=(8, 4))
                for g in por_qtd[qtd]:
                    bloco_vars.append(self._linha(g, selecionavel=True))
                self._blocos.append((bloco_master, bloco_vars))
        else:
            ttk.Label(self.lista, text=f"Tudo impresso em {dia_txt}! 🎉",
                      padding=(0, 12)).pack()

        # ----- Seção: já impressas (arquivadas), embaixo e separadas
        if arquivadas:
            cab_arq = ttk.Frame(self.lista)
            cab_arq.pack(fill="x", pady=(16, 2))
            ttk.Label(cab_arq,
                      text=f"✓  Já impressas — arquivadas ({len(arquivadas)})",
                      font=("Segoe UI", 11, "bold"), foreground=CINZA
                      ).pack(side="left")
            # Recuperacao de impressao (papel atolado/picotado): marca as caixinhas
            # das arquivadas e reimprime varias de uma vez, sem mexer no estado.
            ttk.Button(cab_arq, text="↻ Reimprimir marcadas",
                       command=self.reimprimir_marcadas).pack(side="right")
            for g in arquivadas:
                self._linha(g, arquivada=True)

        self._ocupar(False, f"Atualizado às {datetime.now():%H:%M}")

    def _linha(self, g, selecionavel: bool = False, arquivada: bool = False):
        status = self.prov.status_grupo(self.estado, g)
        faltam = len(self.prov.envios_pendentes(self.estado, g))
        fr = ttk.Frame(self.lista, padding=(8, 6), relief="solid", borderwidth=1)
        fr.pack(fill="x", pady=2)

        var = None
        if selecionavel:                       # caixinha para "Imprimir selecionados"
            var = tk.BooleanVar(value=(g.chave, g.quantidade) in self._sel_antes)
            ttk.Checkbutton(fr, variable=var,
                            command=self._atualizar_contagem).pack(side="left", padx=(0, 6))
            self._sel_vars.append((g, var))
        elif arquivada:                        # caixinha para "Reimprimir marcadas"
            var = tk.BooleanVar(value=False)
            ttk.Checkbutton(fr, variable=var).pack(side="left", padx=(0, 6))
            self._sel_arq.append((g, var))

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

        # Rastreio (AWB) — so em grupos Shopee de 1 pedido ja impresso. Empacotado
        # por ultimo entre os "right", aparece a esquerda dos botoes (no meio da
        # linha), para conferir com a etiqueta e o site.
        if getattr(g, "rastreio", ""):
            ttk.Label(fr, text=f"🏷 {g.rastreio}", foreground=VERDE,
                      font=("Consolas", 10, "bold")).pack(side="right", padx=12)

        return var          # BooleanVar da caixinha (ou None se nao selecionavel)

    # -------------------------------------------------------------- IMPRIMIR
    # CONTRATO DE IMPRESSAO (invariante 1 — NAO reordenar):
    #   1. GERA as etiquetas (ZIP na Downloads) SEM marcar estado
    #      -> self.prov.imprimir_lotes(...), que devolve os pendentes e nao marca;
    #   2. CONFIRMA fisicamente com o operador ("as etiquetas sairam certo?")
    #      -> _confirmar_e_marcar pergunta antes de qualquer marcacao;
    #   3. So entao MARCA como impresso -> self.prov.marcar_impresso(...).
    # Marcar antes da confirmacao faria um grupo sumir da lista sem etiqueta
    # fisica (Zebra pode atolar). Individual e lote passam pelo MESMO caminho.
    def _confirmar_organizar(self, grupos: list) -> bool:
        """Na Shopee, organizar o envio compromete a Postagem — pede confirmação
        antes (conta os pedidos pendentes, sem rede). O organizar é idempotente:
        pula quem já tem AWB. No ML, nunca há o que organizar → segue direto."""
        if not self.prov.organiza_envio:
            return True
        n = sum(len(self.prov.envios_pendentes(self.estado, g)) for g in grupos)
        if n == 0:
            return True
        return messagebox.askyesno(
            "Organizar envio",
            f"Organizar (se preciso) e imprimir {n} pedido(s) como Postagem (drop-off)?\n\n"
            "Isso confirma o método de envio na Shopee.")

    def imprimir(self, g) -> None:
        """Impressao individual pelo MESMO fluxo do lote: gera a etiqueta, a tela
        pergunta "as etiquetas sairam corretamente?" e SO ENTAO marca como
        impresso. Antes, o caminho individual marcava assim que o ZIP era gerado
        — se a Zebra atolasse, o grupo ja constava impresso sem etiqueta fisica."""
        if self.ocupado:
            return
        if not self._confirmar_organizar([g]):
            return
        self._ocupar(True, f"Imprimindo: {g.nome} ...")
        threading.Thread(target=self._gerar_sem_marcar_thread,
                         args=([g],), daemon=True).start()

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
            self.prov.reimprimir(g)
        except Exception as e:
            self.root.after(0, lambda erro=e: self._erro(str(erro)))
            return
        self.root.after(0, self._render)

    def reimprimir_marcadas(self) -> None:
        """Reimprime de uma vez todas as arquivadas com a caixinha marcada
        (recuperacao de papel atolado/picotado). O controle de impresso nao muda."""
        if self.ocupado:
            return
        alvo = [g for g, v in self._sel_arq if v.get()]
        if not alvo:
            messagebox.showinfo("Reimprimir",
                                "Marque ao menos uma arquivada na caixinha à esquerda.")
            return
        total = sum(g.total_etiquetas for g in alvo)
        if not messagebox.askyesno(
                "Reimprimir marcadas",
                f"Reimprimir {total} etiqueta(s) de {len(alvo)} grupo(s)?\n\n"
                "O controle de impresso não muda."):
            return
        self._ocupar(True, f"Reimprimindo {len(alvo)} grupo(s) ...")
        threading.Thread(target=self._reimprimir_marcadas_thread,
                         args=(alvo,), daemon=True).start()

    def _reimprimir_marcadas_thread(self, alvo: list) -> None:
        # Um grupo que falhar nao derruba os demais: gera o que der e avisa.
        falhas = []
        for g in alvo:
            try:
                self.prov.reimprimir(g)
            except Exception as e:               # noqa: BLE001
                falhas.append((g.nome, str(e)))
        self.root.after(0, lambda: self._pos_reimpressao(len(alvo), falhas))

    def _pos_reimpressao(self, n: int, falhas: list) -> None:
        self._ocupar(False, f"{n - len(falhas)} reimpressão(ões) enviada(s).")
        log.info("Reimpressao: %d enviada(s), %d falha(s) (nao altera estado)",
                 n - len(falhas), len(falhas))
        if falhas:
            linhas = "\n".join(f"• {nome}: {motivo}" for nome, motivo in falhas[:8])
            mais = "" if len(falhas) <= 8 else f"\n(+{len(falhas) - 8} outra(s))"
            messagebox.showwarning(
                "Algumas reimpressões falharam",
                f"{len(falhas)} grupo(s) não foram reimpressos:\n\n{linhas}{mais}")
        self._render()

    # ------------------------------------------------------- IMPRIMIR LOTES
    def imprimir_lotes(self) -> None:
        if self.ocupado:
            return
        selecionados = [g for g, v in self._sel_vars if v.get()]
        if not selecionados:
            messagebox.showinfo("Imprimir lotes",
                                "Marque ao menos um lote na caixinha à esquerda.")
            return
        if not self._confirmar_organizar(selecionados):
            return
        if self.prov.suporta_identificacao:
            extra = f" ({self._ident_labels.get(self.modo_ident, '')})"
        else:
            extra = ""
        self._ocupar(True, f"Imprimindo {len(selecionados)} lote(s){extra} ...")
        threading.Thread(target=self._gerar_sem_marcar_thread,
                         args=(selecionados,), daemon=True).start()

    def _gerar_sem_marcar_thread(self, grupos) -> None:
        """PASSO 1 do contrato: gera as etiquetas (ZIP na Downloads) e devolve os
        pendentes de cada grupo. NAO marca estado aqui — imprimir_lotes do provedor
        so gera. Ao terminar, entrega a _confirmar_e_marcar (passos 2 e 3)."""
        log.info("Gerar etiquetas: %s, %d grupo(s), ident=%s",
                 self._ctx_log(), len(grupos), self.modo_ident)
        try:
            impressos, falhas = self.prov.imprimir_lotes(grupos, self.estado, modo=self.modo_ident)
        except Exception as e:
            self.root.after(0, lambda erro=e: self._erro(str(erro)))
            return
        self.root.after(0, lambda: self._confirmar_e_marcar(impressos, falhas))

    def _confirmar_e_marcar(self, impressos: list, falhas: list | None = None) -> None:
        """PASSOS 2 e 3 do contrato: pergunta ao operador se as etiquetas sairam
        certo (passo 2) e SO ENTAO marca como impresso (passo 3). Este e o UNICO
        ponto da GUI que chama marcar_impresso — nao marque em outro lugar, senao
        um grupo pode constar impresso sem etiqueta fisica (invariante 1)."""
        self._ocupar(False, "")
        falhas = falhas or []
        if falhas:                              # alguns pedidos nao geraram (parcial)
            log.warning("Lote parcial: %d pedido(s) nao sairam (%s)", len(falhas),
                        ", ".join(str(sn) for sn, _ in falhas[:10]))
            linhas = "\n".join(f"• {sn}: {motivo}" for sn, motivo in falhas[:8])
            mais = "" if len(falhas) <= 8 else f"\n(+{len(falhas) - 8} outro(s))"
            messagebox.showwarning(
                "Alguns pedidos não saíram",
                f"{len(falhas)} pedido(s) não foram impressos:\n\n{linhas}{mais}\n\n"
                "Os demais foram enviados para a impressora.")
        if not impressos:
            if not falhas:
                messagebox.showinfo("Imprimir lotes", "Nada pendente nos lotes selecionados.")
            return
        n = len(impressos)
        etiquetas = sum(len(pend) for _, pend in impressos)
        # Sempre confirma o resultado fisico antes de marcar (convencao "lotes
        # confirmam antes de marcar"), inclusive quando e um unico lote.
        marcar = messagebox.askyesno(
            "Confirmar impressão",
            f"Enviei {n} lote(s) para a impressora.\n\n"
            "As etiquetas saíram corretamente?\n\n"
            "Sim = marca como impressos.\n"
            "Não = mantém pendentes para reimprimir.")
        if marcar:
            for g, pend in impressos:
                self.prov.marcar_impresso(self.estado, g, pend)
            log.info("Confirmado: %d grupo(s), %d etiqueta(s) marcados como impressos (%s)",
                     n, etiquetas, self._ctx_log())
        else:
            log.info("Nao confirmado: %d lote(s) mantidos pendentes para reimprimir", n)
        self._render()

    def imprimir_proximo(self) -> None:
        # Inclui grupos "parcial" (alguns envios novos a imprimir), nao so "pendente".
        pend = next((g for g in self.grupos
                     if self.prov.status_grupo(self.estado, g) != "impresso"), None)
        if not pend:
            messagebox.showinfo("Tudo certo", "Nenhum grupo pendente. 🎉")
            return
        self.imprimir(pend)

    # --------------------------------------------------------- EDITOR DE NOMES
    def abrir_editor_nomes(self) -> None:
        """Janela para incluir/alterar/remover os nomes amigaveis (SKU -> nome)
        sem editar o JSON na mao. Grava via core.salvar_nomes (atomico) e aplica
        na lista atual ao fechar, sem precisar reatualizar."""
        EditorNomes(self)


class EditorNomes:
    """Janelinha de edicao do de-para SKU -> nome amigavel."""

    def __init__(self, app: "SeparadorApp") -> None:
        self.app = app
        self.nomes = dict(core.carregar_nomes())     # copia de trabalho
        self.alterado = False

        win = tk.Toplevel(app.root)
        self.win = win
        win.title("Nomes amigáveis (SKU → nome)")
        win.geometry("560x520")
        win.transient(app.root)
        win.protocol("WM_DELETE_WINDOW", self._fechar)

        # Busca
        topo = ttk.Frame(win, padding=(10, 10, 10, 4))
        topo.pack(fill="x")
        ttk.Label(topo, text="Buscar:").pack(side="left", padx=(0, 6))
        self.busca_var = tk.StringVar()
        self.busca_var.trace_add("write", lambda *_: self._preencher_lista())
        e = ttk.Entry(topo, textvariable=self.busca_var)
        e.pack(side="left", fill="x", expand=True)
        e.focus_set()

        # Lista (SKU | Nome)
        meio = ttk.Frame(win, padding=(10, 0))
        meio.pack(fill="both", expand=True)
        cols = ("sku", "nome")
        self.tree = ttk.Treeview(meio, columns=cols, show="headings", selectmode="browse")
        self.tree.heading("sku", text="SKU")
        self.tree.heading("nome", text="Nome")
        self.tree.column("sku", width=120, anchor="w")
        self.tree.column("nome", width=380, anchor="w")
        sb = ttk.Scrollbar(meio, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self._selecionar)

        # Campos de edicao
        edit = ttk.Frame(win, padding=(10, 6))
        edit.pack(fill="x")
        ttk.Label(edit, text="SKU:").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=2)
        self.sku_var = tk.StringVar()
        ttk.Entry(edit, textvariable=self.sku_var, width=18).grid(row=0, column=1, sticky="w")
        ttk.Label(edit, text="Nome:").grid(row=1, column=0, sticky="w", padx=(0, 6), pady=2)
        self.nome_var = tk.StringVar()
        ent_nome = ttk.Entry(edit, textvariable=self.nome_var)
        ent_nome.grid(row=1, column=1, columnspan=2, sticky="we", pady=2)
        ent_nome.bind("<Return>", lambda _e: self._salvar_um())
        edit.columnconfigure(1, weight=1)

        # Botoes
        acoes = ttk.Frame(win, padding=(10, 4, 10, 10))
        acoes.pack(fill="x")
        ttk.Button(acoes, text="↑", width=3,
                   command=lambda: self._mover(-1)).pack(side="left")
        ttk.Button(acoes, text="↓", width=3,
                   command=lambda: self._mover(1)).pack(side="left", padx=(4, 12))
        ttk.Button(acoes, text="🗑 Remover", command=self._remover).pack(side="left")
        ttk.Button(acoes, text="Fechar", command=self._fechar).pack(side="right")
        ttk.Button(acoes, text="💾 Salvar", command=self._salvar_um).pack(side="right", padx=6)

        # Dica: a ordem da lista = ordem de separacao/impressao do bloco "qtd 1".
        ttk.Label(win, foreground=CINZA, padding=(10, 0, 10, 8),
                  text="A ordem desta lista define a ordem de impressão do bloco "
                       "“Quantidade por pedido = 1”. Use ↑ ↓ para ajustar.").pack(fill="x")

        self._preencher_lista()

    def _preencher_lista(self) -> None:
        # Exibe na ORDEM SALVA (nao alfabetica): essa ordem e a ordem de separacao
        # do bloco "qtd 1", ajustada pelas setas ↑/↓.
        termo = self.busca_var.get().strip().lower()
        self.tree.delete(*self.tree.get_children())
        for sku, nome in self.nomes.items():
            if termo and termo not in sku.lower() and termo not in nome.lower():
                continue
            self.tree.insert("", "end", iid=sku, values=(sku, nome))

    def _mover(self, delta: int) -> None:
        """Sobe/desce o SKU selecionado na ordem (define a ordem do bloco 'qtd 1').
        Opera na lista COMPLETA — se houver busca ativa, limpe-a para ver o efeito."""
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Ordenar", "Selecione um SKU da lista para mover.",
                                parent=self.win)
            return
        sku = sel[0]
        chaves = list(self.nomes.keys())
        i = chaves.index(sku)
        j = i + delta
        if j < 0 or j >= len(chaves):
            return                                 # ja esta no topo/fundo
        chaves[i], chaves[j] = chaves[j], chaves[i]
        self.nomes = {k: self.nomes[k] for k in chaves}   # reconstroi na nova ordem
        self.alterado = True
        self._gravar()
        self._preencher_lista()
        self.tree.selection_set(sku)
        self.tree.see(sku)

    def _selecionar(self, _event=None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        sku = sel[0]
        self.sku_var.set(sku)
        self.nome_var.set(self.nomes.get(sku, ""))

    def _salvar_um(self) -> None:
        sku = self.sku_var.get().strip()
        nome = self.nome_var.get().strip()
        if not sku or not nome:
            messagebox.showinfo("Nomes", "Preencha o SKU e o nome.", parent=self.win)
            return
        self.nomes[sku] = nome
        self.alterado = True
        self._gravar()
        self._preencher_lista()
        if self.tree.exists(sku):
            self.tree.selection_set(sku)
            self.tree.see(sku)

    def _remover(self) -> None:
        sku = self.sku_var.get().strip()
        if sku not in self.nomes:
            messagebox.showinfo("Nomes", "Selecione um SKU da lista para remover.",
                                parent=self.win)
            return
        if not messagebox.askyesno("Remover", f"Remover o nome do SKU '{sku}'?",
                                   parent=self.win):
            return
        del self.nomes[sku]
        self.alterado = True
        self._gravar()
        self.sku_var.set("")
        self.nome_var.set("")
        self._preencher_lista()

    def _gravar(self) -> None:
        try:
            core.salvar_nomes(self.nomes)
        except Exception as e:                       # noqa: BLE001
            messagebox.showerror("Nomes", f"Não consegui salvar:\n{e}", parent=self.win)

    def _fechar(self) -> None:
        # Reaplica os nomes E reordena a lista ja carregada (a nova ordem do bloco
        # "qtd 1" aparece na hora, sem precisar reatualizar).
        if self.alterado and self.app.grupos:
            core.aplicar_nomes(self.app.grupos, self.nomes)
            self.app.grupos = core.ordenar_grupos(self.app.grupos)
            try:
                self.app._render()
            except Exception:                        # noqa: BLE001
                pass
        self.win.destroy()


def main() -> None:
    root = tk.Tk()
    SeparadorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
