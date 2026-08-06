#!/usr/bin/env python3
"""Diagnostico SO-LEITURA da ESTRUTURA de um lote de etiquetas (ZIP ou .txt).

Serve para responder "por que saiu uma etiqueta em branco no meio do lote?"
sem depender de palpite: mostra, bloco a bloco, o que o arquivo REALMENTE
manda para a impressora.

O que ele procura (as tres causas possiveis de pagina em branco):

  1. BLOCO VAZIO no arquivo (`^XA^XZ` sem conteudo) -- seria culpa do ML ou
     nossa. Obs.: o app da Zebra IGNORA bloco vazio (_validar_e_extrair_blocos_zpl),
     entao mesmo se existir ele nao chega a imprimir -- mas e bom saber.

  2. MODO DE MIDIA trocando no meio do lote (`^MN`) -- e o suspeito mais forte
     de "as vezes pula uma etiqueta". `^MNN` = midia continua (imprime pelo
     comprimento, ignora o sensor de gap); `^MNY`/`^MNM` = usa o sensor. Se um
     bloco vem continuo e o seguinte volta a usar o sensor, a impressora avanca
     ate achar o proximo gap -- e esse avanco sai como etiqueta em branco.

  3. COMPRIMENTO (`^LL`) divergente entre os blocos, pelo mesmo motivo.

  Fora do arquivo sobra uma 4a causa, que este script NAO ve: o auto-feed de
  inicio de sessao do proprio app da Zebra (`^XA^XZ` proposital, para
  posicionar o sensor). Esse aparece no log dele como
  "Avancando etiqueta - posicionando sensor...". Se o log tem essa linha e o
  arquivo esta limpo aqui, a etiqueta em branco e a do auto-feed.

PRIVACIDADE: nunca imprime conteudo de campo (`^FD`) -- as etiquetas levam
nome, endereco e CEP do comprador. So sai nome de comando, contagem e tamanho.

Uso:
    python tools/diag_zpl.py                 # pega o lote mais recente sozinho
    python tools/diag_zpl.py <arquivo.zip>
    python tools/diag_zpl.py <arquivo.txt>
"""
from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path

# Comandos que mexem em midia/comprimento/copias -- os que podem gerar avanco
# de etiqueta. Sao os unicos cujo VALOR e mostrado (nao carregam dado pessoal).
COMANDOS_MIDIA = ("LL", "PW", "MN", "MM", "LH", "LT", "PQ", "JM", "LS")
RE_BLOCO = re.compile(r"\^XA(.*?)\^XZ", re.DOTALL | re.IGNORECASE)
RE_MIDIA = re.compile(r"\^(" + "|".join(COMANDOS_MIDIA) + r")([^\^~\n]*)", re.IGNORECASE)
# Um bloco "desenha" se tem campo de texto, grafico inline ou imagem da RAM.
RE_DESENHA = re.compile(r"\^(FD|FN|GF|GB|XG|BC|B3|BY)", re.IGNORECASE)
# A etiqueta de ENVIO do ML e a que traz grafico inline (^GF); a nota traz texto.
# Mesma classificacao que o app da Zebra usa em _verificar_sequencia_ml.
RE_ENVIO = re.compile(r"\^GF", re.IGNORECASE)

PREFIXOS = ("etiqueta de envio", "etiqueta shopee")


def _candidatos() -> list[Path]:
    """Lotes recentes, do mais novo para o mais antigo: primeiro a pasta de
    retencao do app da Zebra (>= v1.26.2, o que imprimiu com sucesso vai para
    la), depois a Downloads (o que ainda nao foi impresso)."""
    casa = Path.home()
    achados: list[Path] = []
    for pasta in (casa / "zebra_usb_concluidos", casa / "Downloads"):
        if not pasta.is_dir():
            continue
        for p in pasta.rglob("*"):
            if p.is_file() and p.suffix.lower() in (".zip", ".txt", ".zpl", ".plain"):
                if any(p.name.lower().startswith(x) for x in PREFIXOS):
                    achados.append(p)
    return sorted(achados, key=lambda p: p.stat().st_mtime, reverse=True)


def _texto_do_arquivo(caminho: Path) -> str:
    if caminho.suffix.lower() == ".zip":
        partes = []
        with zipfile.ZipFile(caminho) as zf:
            for nome in zf.namelist():
                partes.append(zf.read(nome).decode("utf-8", errors="ignore"))
        return "\n".join(partes)
    return caminho.read_bytes().decode("utf-8", errors="ignore")


def _midia(bloco: str) -> dict[str, str]:
    """{comando: valor} dos comandos de midia presentes no bloco."""
    return {m.group(1).upper(): m.group(2).strip() for m in RE_MIDIA.finditer(bloco)}


def _vendas_sem_danfe(blocos: list[dict]) -> list[int]:
    """Numeros dos blocos de ENVIO que nao sao seguidos do seu DANFE.

    O ML manda ENVIO -> DANFE por venda; a sequencia ENVIO -> ENVIO significa
    uma venda que sairia SEM a nota. Mesma regra que o app da Zebra aplica em
    _verificar_sequencia_ml -- conferida aqui tambem porque este lado ve o
    arquivo ANTES de imprimir, e porque um diagnostico que so olha 'saiu pagina
    em branco?' cala diante de um defeito pior no mesmo arquivo."""
    faltando: list[int] = []
    pendente: int | None = None
    for b in blocos:
        if b["envio"]:
            if pendente is not None:
                faltando.append(pendente)
            pendente = b["n"]
        elif b["danfe"]:
            pendente = None
    if pendente is not None:
        faltando.append(pendente)
    return faltando


def analisar(texto: str) -> tuple[list[dict], list[str]]:
    """Devolve (blocos, avisos). Cada bloco: indice, bytes, campos, danfe,
    envio, vazio, midia."""
    blocos: list[dict] = []
    for i, m in enumerate(RE_BLOCO.finditer(texto), 1):
        interior = m.group(1)
        blocos.append({
            "n": i,
            "bytes": len(m.group(0)),
            "campos": len(RE_DESENHA.findall(interior)),
            "danfe": "DANFE" in interior.upper(),
            "envio": bool(RE_ENVIO.search(interior)),
            "vazio": not interior.strip(),
            "midia": _midia(interior),
        })

    avisos: list[str] = []
    vazios = [b["n"] for b in blocos if b["vazio"] or b["campos"] == 0]
    if vazios:
        avisos.append(
            f"BLOCO EM BRANCO no arquivo: #{', #'.join(str(v) for v in vazios)} "
            "(sem nenhum campo a desenhar). Origem: ML ou este app."
        )

    # Emparelhamento ENVIO/DANFE -- so faz sentido para o ML (a Shopee e 1
    # etiqueta por venda, sem nota junto, e usa ~DG para a imagem).
    if any(b["danfe"] for b in blocos) and "~DG" not in texto.upper():
        sem_nota = _vendas_sem_danfe(blocos)
        if sem_nota:
            avisos.append(
                f"VENDA SEM DANFE: o(s) bloco(s) de envio #{', #'.join(str(v) for v in sem_nota)} "
                "nao vem seguido(s) da nota. Essa venda sairia com a etiqueta e SEM a "
                "nota fiscal. Origem: o pacote que o ML devolveu."
            )
        if len(blocos) % 2:
            avisos.append(
                f"Total IMPAR de blocos ({len(blocos)}): o ML manda 1 etiqueta + 1 DANFE "
                "por venda, entao o esperado e par."
            )

    for cmd in ("MN", "LL"):
        # 'ausente' conta como valor: um comando que persiste (modo de midia,
        # comprimento) posto em alguns blocos e nao em outros tambem e uma
        # TROCA de estado no meio do lote. So compara se algum bloco o traz --
        # senao todo lote sem esses comandos viraria alarme falso.
        if not any(cmd in b["midia"] for b in blocos):
            continue
        valores = {b["midia"].get(cmd, "(ausente)") for b in blocos}
        if len(valores) > 1:
            avisos.append(
                f"^{cmd} MUDA no meio do lote: {sorted(valores)}. Trocar de modo de "
                "midia/comprimento entre etiquetas faz a impressora avancar ate o "
                "proximo gap -- e o avanco sai como etiqueta em branco."
            )

    copias = {b["midia"]["PQ"] for b in blocos if b["midia"].get("PQ")}
    fora = [c for c in copias if not c.split(",")[0].strip() in ("", "1")]
    if fora:
        avisos.append(f"^PQ pedindo mais de 1 copia: {sorted(fora)}.")

    return blocos, avisos


def main() -> int:
    if len(sys.argv) > 1:
        caminho = Path(sys.argv[1]).expanduser()
        if not caminho.is_file():
            print(f"Arquivo nao encontrado: {caminho}")
            return 1
    else:
        achados = _candidatos()
        if not achados:
            print("Nenhum lote encontrado em ~/zebra_usb_concluidos nem em ~/Downloads.")
            print("Passe o caminho na mao: python tools/diag_zpl.py <arquivo.zip>")
            return 1
        caminho = achados[0]
        print(f"(sem argumento: peguei o mais recente de {len(achados)} encontrados)")

    print(f"\nArquivo: {caminho}")
    blocos, avisos = analisar(_texto_do_arquivo(caminho))
    if not blocos:
        print("Nenhum bloco ^XA...^XZ no arquivo.")
        return 1

    sem_nota = set(_vendas_sem_danfe(blocos)) if any(b["danfe"] for b in blocos) else set()
    print(f"Blocos (paginas) que serao impressos: {len(blocos)}\n")
    for b in blocos:
        if b["danfe"]:
            rotulo = "DANFE "
        elif b["envio"]:
            rotulo = "ENVIO "
        else:
            rotulo = "      "
        marca = ""
        if b["vazio"] or b["campos"] == 0:
            marca = "  <== EM BRANCO"
        elif b["n"] in sem_nota:
            marca = "  <== SEM DANFE"
        midia = " ".join(f"^{k}{v}" for k, v in sorted(b["midia"].items())) or "-"
        print(f"  #{b['n']:>3}  {b['bytes']:>8} B  campos={b['campos']:<4} "
              f"{rotulo}{midia}{marca}")

    print()
    for a in avisos:
        print(f"  !! {a}")
    if not any("EM BRANCO" in a for a in avisos):
        print("  Pagina em branco: NAO veio deste arquivo (nenhum bloco vazio, nenhuma")
        print("  troca de midia/comprimento). Procure no log do app da Zebra a linha")
        print("  'Avancando etiqueta - posicionando sensor' (auto-feed de inicio de")
        print("  sessao); se nao houver, calibre a midia.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
