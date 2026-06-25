"""
gui_screenshot.py
Roda a GUI do separador (separador_gui.py) headless, sob um display virtual,
e salva um PNG — para validar mudancas VISUAIS em ambientes sem monitor
(ex.: Claude Code na web, onde nao ha display).

Uso (com xvfb fornecendo o display):
  xvfb-run -a python3.12 tools/gui_screenshot.py [saida.png] [marketplace]

  saida.png    caminho do PNG de saida   (padrao: gui.png)
  marketplace  "Shopee" | "Mercado Livre" (padrao: Mercado Livre)

Pre-requisitos: tkinter + imagemagick (o `import`). O script
tools/setup_gui_tests.sh instala tudo. Abre na TELA INICIAL (nao busca
pedidos), entao nao precisa de rede nem de credenciais.
"""
import os
import sys
import time
import tkinter as tk

# Permite rodar de qualquer cwd (o projeto e a pasta-mae de tools/).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import separador_gui as gui  # noqa: E402

saida = sys.argv[1] if len(sys.argv) > 1 else "gui.png"
marketplace = sys.argv[2] if len(sys.argv) > 2 else "Mercado Livre"

root = tk.Tk()
app = gui.SeparadorApp(root)
if marketplace != "Mercado Livre":
    app.marketplace_var.set(marketplace)   # reflete no radio
    app._trocar_marketplace(marketplace)
root.update()
time.sleep(0.3)                            # deixa o WM/render assentar
os.system(f"import -window root {saida}")  # captura a tela do display virtual
root.destroy()
print(f"Screenshot salvo: {saida}  (marketplace: {marketplace})")
