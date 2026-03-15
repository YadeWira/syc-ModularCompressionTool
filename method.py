"""
method.py - Resuelve y descompone cadenas de métodos compuestos de SYC/FreeArc

Formato de cadena:
  compresor1:opt1:opt2+compresor2:opt1+compresor3
  
  Ejemplo: xprecomp+srep:m5f:a0+zstd:22
"""

from dataclasses import dataclass
from typing import List



@dataclass
class MethodStep:
    """Un paso individual en la cadena de compresión"""
    compressor: str          # nombre del compresor (ej: "zstd")
    options: List[str]       # opciones posicionales (ej: ["22"])
    raw: str                 # string original (ej: "zstd:22")


class MethodChain:
    """
    Representa una cadena de compresores a aplicar en secuencia.
    
    Ej: "xprecomp+srep:m5f:a0+zstd:22"
    -> [MethodStep("xprecomp", []), MethodStep("srep", ["m5f","a0"]), MethodStep("zstd", ["22"])]
    """

    def __init__(self, steps: List[MethodStep]):
        self.steps = steps

    @classmethod
    def parse(cls, chain_str: str) -> "MethodChain":
        """Parsea una cadena de método en pasos individuales"""
        steps = []
        for part in chain_str.split("+"):
            part = part.strip()
            if not part:
                continue
            tokens = part.split(":")
            compressor = tokens[0]
            options = tokens[1:] if len(tokens) > 1 else []
            steps.append(MethodStep(
                compressor=compressor,
                options=options,
                raw=part
            ))
        return cls(steps)

    def reversed_steps(self) -> List[MethodStep]:
        """Devuelve los pasos en orden inverso (para descompresión)"""
        return list(reversed(self.steps))

    def __repr__(self):
        return f"MethodChain({' -> '.join(s.raw for s in self.steps)})"


def build_cmd(template: str, step: MethodStep,
              datafile: str, packedfile: str,
              extra_options: str = "") -> str:
    """
    Construye el comando final reemplazando los placeholders del .ini:
    
      {options}         -> opciones separadas por espacios
      {:option}         -> opciones pegadas con ':'
      {compressor}      -> nombre del compresor
      $$arcdatafile$$   -> archivo de entrada
      $$arcpackedfile$$ -> archivo de salida
      <stdin>           -> marcador de stdin (para pipelines)
      <stdout>          -> marcador de stdout (para pipelines)
    """
    options_str = " ".join(step.options) if step.options else extra_options
    option_joined = (":" + ":".join(step.options)) if step.options else ""

    cmd = template
    cmd = cmd.replace("{compressor}", step.compressor)
    cmd = cmd.replace("{options}", options_str)
    cmd = cmd.replace("{:option}", option_joined)
    import re as _re
    # Reemplazar cualquier variante de extension: $$arcpackedfile$$.zpaq, .nz, .tmp, etc.
    cmd = _re.sub(r'\$\$arcdatafile\$\$(?:\.[a-zA-Z0-9]+)?',
                  lambda m: datafile, cmd)
    cmd = _re.sub(r'\$\$arcpackedfile\$\$(?:\.[a-zA-Z0-9]+)?',
                  lambda m: packedfile, cmd)

    return cmd