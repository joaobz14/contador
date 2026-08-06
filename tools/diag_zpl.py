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


def analisar(texto: str) -> tuple[list[dict], list[str]]:
    """Devolve (blocos, avisos). Cada bloco: indice, bytes, campos, danfe,
    vazio, midia."""
    blocos: list[dict] = []
    for i, m in enumerate(RE_BLOCO.finditer(texto), 1):
        interior = m.group(1)
        blocos.append({
            "n": i,
            "bytes": len(m.group(0)),
            "campos": len(RE_DESENHA.findall(interior)),
            "danfe": "DANFE" in interior.upper(),
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

    for cmd in ("MN", "LL"):
        valores = {b["midia"].get(cmd, "") for b in blocos if cmd in b["midia"]}
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

    print(f"Blocos (paginas) que serao impressos: {len(blocos)}\n")
    for b in blocos:
        rotulo = "DANFE " if b["danfe"] else "      "
        marca = "  <== EM BRANCO" if b["vazio"] or b["campos"] == 0 else ""
        midia = " ".join(f"^{k}{v}" for k, v in sorted(b["midia"].items())) or "-"
        print(f"  #{b['n']:>3}  {b['bytes']:>8} B  campos={b['campos']:<4} "
              f"{rotulo}{midia}{marca}")

    print()
    if avisos:
        for a in avisos:
            print(f"  !! {a}")
    else:
        print("  OK: nenhum bloco em branco e nenhuma troca de midia/comprimento.")
        print("     Se saiu etiqueta em branco, ela NAO veio deste arquivo -- procure")
        print("     no log do app da Zebra a linha 'Avancando etiqueta - posicionando")
        print("     sensor' (auto-feed de inicio de sessao) ou calibre a midia.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
