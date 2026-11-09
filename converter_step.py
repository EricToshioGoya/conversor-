import json
import os
import sys
import time

import cadquery as cq

# Tolerancias da malha: valores maiores geram arquivos .glb menores e menos precisos
TOLERANCIA_LINEAR = 0.5   # mm
TOLERANCIA_ANGULAR = 0.3  # rad
PASTA_SAIDA = "saida_glb"


def tamanho_mb(caminho):
    return round(os.path.getsize(caminho) / 1e6, 2)


def ler_arvore(caminho, max_nivel=3, max_filhos=15):
    # Le a arvore de montagem com nomes (XCAF). Falha aqui nao interrompe a conversao.
    try:
        from OCP.STEPCAFControl import STEPCAFControl_Reader
        from OCP.TDocStd import TDocStd_Document
        from OCP.XCAFApp import XCAFApp_Application
        from OCP.TCollection import TCollection_ExtendedString
        from OCP.XCAFDoc import XCAFDoc_DocumentTool, XCAFDoc_ShapeTool
        from OCP.TDF import TDF_LabelSequence, TDF_Label
        from OCP.TDataStd import TDataStd_Name

        app = XCAFApp_Application.GetApplication_s()
        doc = TDocStd_Document(TCollection_ExtendedString("XmlOcaf"))
        app.NewDocument(TCollection_ExtendedString("MDTV-XCAF"), doc)

        leitor = STEPCAFControl_Reader()
        leitor.SetNameMode(True)
        leitor.ReadFile(caminho)
        leitor.Transfer(doc)

        ferramenta = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
        linhas = []

        def nome(rotulo):
            attr = TDataStd_Name()
            if rotulo.FindAttribute(TDataStd_Name.GetID_s(), attr):
                return attr.Get().ToExtString()
            return "(sem nome)"

        def percorrer(rotulo, nivel):
            linhas.append("  " * nivel + nome(rotulo))
            if nivel >= max_nivel:
                return
            filhos = TDF_LabelSequence()
            XCAFDoc_ShapeTool.GetComponents_s(rotulo, filhos)
            for i in range(1, min(filhos.Length(), max_filhos) + 1):
                comp = filhos.Value(i)
                ref = TDF_Label()
                if XCAFDoc_ShapeTool.GetReferredShape_s(comp, ref):
                    percorrer(ref, nivel + 1)
                else:
                    percorrer(comp, nivel + 1)

        raizes = TDF_LabelSequence()
        ferramenta.GetFreeShapes(raizes)
        for i in range(1, raizes.Length() + 1):
            percorrer(raizes.Value(i), 0)
        return linhas
    except Exception as erro:
        return ["(nao foi possivel ler os nomes: %s)" % erro]


def exportar_glb(modelo, base, destino):
    montagem = cq.Assembly()
    montagem.add(modelo, name=base)
    # Versoes mais antigas do CadQuery so tem save(); checar o metodo evita mascarar erros reais
    exportar = montagem.export if hasattr(montagem, "export") else montagem.save
    exportar(destino, "GLTF",
             tolerance=TOLERANCIA_LINEAR,
             angularTolerance=TOLERANCIA_ANGULAR)


def processar(caminho, pasta_saida):
    inicio = time.time()
    base = os.path.splitext(os.path.basename(caminho))[0]
    print("\n=== %s (%s MB) ===" % (os.path.basename(caminho), tamanho_mb(caminho)))

    print("Lendo o STEP...")
    modelo = cq.importers.importStep(caminho)
    solidos = modelo.solids().vals()
    caixa = cq.Compound.makeCompound(modelo.vals()).BoundingBox()
    volume = sum(s.Volume() for s in solidos)
    print("Solidos: %d" % len(solidos))
    print("Dimensoes X, Y, Z (mm): %.1f, %.1f, %.1f" % (caixa.xlen, caixa.ylen, caixa.zlen))

    print("Lendo nomes da montagem...")
    arvore = ler_arvore(caminho)
    for linha in arvore[:40]:
        print(linha)

    os.makedirs(pasta_saida, exist_ok=True)
    caminho_glb = os.path.join(pasta_saida, base + ".glb")
    print("Gerando o .glb...")
    exportar_glb(modelo, base, caminho_glb)

    meta = {
        "arquivo": os.path.basename(caminho),
        "tamanho_step_mb": tamanho_mb(caminho),
        "tamanho_glb_mb": tamanho_mb(caminho_glb),
        "solidos": len(solidos),
        "dimensoes_mm": {"x": round(caixa.xlen, 2), "y": round(caixa.ylen, 2), "z": round(caixa.zlen, 2)},
        "volume_total_mm3": round(volume, 2),
        "arvore": arvore,
        "tolerancia_linear_mm": TOLERANCIA_LINEAR,
        "tolerancia_angular_rad": TOLERANCIA_ANGULAR,
        "tempo_s": round(time.time() - inicio, 1),
    }
    with open(os.path.join(pasta_saida, base + ".json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print("Concluido: STEP %s MB -> GLB %s MB (%.1f s)"
          % (meta["tamanho_step_mb"], meta["tamanho_glb_mb"], meta["tempo_s"]))
    return meta


def listar_entradas(argumentos):
    # Sem argumento: usa a pasta do script. Com argumento: arquivo ou pasta.
    alvo = argumentos[0] if argumentos else os.path.dirname(os.path.abspath(__file__))
    if os.path.isfile(alvo):
        return [alvo]
    return sorted(
        os.path.join(alvo, n) for n in os.listdir(alvo)
        if n.lower().endswith((".step", ".stp"))
    )


def main():
    arquivos = listar_entradas(sys.argv[1:])
    if not arquivos:
        print("Nenhum arquivo .step encontrado.")
        return
    print("%d arquivo(s) para converter." % len(arquivos))

    resumo = []
    for caminho in arquivos:
        pasta_saida = os.path.join(os.path.dirname(os.path.abspath(caminho)), PASTA_SAIDA)
        try:
            resumo.append(processar(caminho, pasta_saida))
        except Exception as erro:
            print("ERRO em %s: %s" % (os.path.basename(caminho), erro))

    print("\n===== RESUMO =====")
    for m in resumo:
        print("%s | STEP %s MB -> GLB %s MB | %d solidos"
              % (m["arquivo"], m["tamanho_step_mb"], m["tamanho_glb_mb"], m["solidos"]))


if __name__ == "__main__":
    main()
