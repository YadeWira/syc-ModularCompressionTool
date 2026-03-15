"""
ini_parser.py - Parsea syc.ini con el mismo formato que arc.ini de FreeArc
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class CompressorDef:
    """Define un compresor externo (sección [External compressor:nombre])"""
    name: str
    header: int = 1
    solid: Optional[int] = None
    packcmd: Optional[str] = None
    unpackcmd: Optional[str] = None
    datafile: Optional[str] = None
    packedfile: Optional[str] = None
    default: Optional[str] = None


class SycIniParser:
    """
    Parsea un archivo .ini con el formato de FreeArc/SYC.
    
    Secciones soportadas:
      [Compression methods]       -> alias de métodos compuestos
      [External compressor:name]  -> definición de compresor externo
    """

    def __init__(self):
        self.methods: Dict[str, str] = {}          # alias -> cadena de método
        self.compressors: Dict[str, CompressorDef] = {}  # nombre -> definición

    def parse_file(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        self._parse_lines(lines)

    def parse_string(self, text: str) -> None:
        self._parse_lines(text.splitlines(keepends=True))

    def _parse_lines(self, lines: List[str]) -> None:
        current_section = None
        current_compressor: Optional[CompressorDef] = None

        for raw_line in lines:
            line = raw_line.strip()

            # Ignorar comentarios y líneas vacías
            if not line or line.startswith(";"):
                continue

            # Detectar sección
            section_match = re.match(r"^\[(.+?)\]$", line)
            if section_match:
                section_name = section_match.group(1)

                if section_name == "Compression methods":
                    current_section = "methods"
                    current_compressor = None

                elif section_name.startswith("External compressor:"):
                    current_section = "compressor"
                    # Puede haber múltiples nombres separados por comas
                    names_raw = section_name[len("External compressor:"):].strip()
                    names = [n.strip() for n in names_raw.split(",")]

                    # Crear definición compartida para todos los nombres del grupo
                    current_compressor = CompressorDef(name=names[0])
                    for name in names:
                        self.compressors[name] = current_compressor
                else:
                    current_section = "unknown"
                    current_compressor = None
                continue

            # Parsear key = value
            kv_match = re.match(r"^(\w+)\s*=\s*(.*)$", line)
            if not kv_match:
                continue

            key = kv_match.group(1).lower()
            value = kv_match.group(2).strip()

            if current_section == "methods":
                # alias = cadena_método
                alias = re.match(r"^(\S+)\s*=\s*(.+)$", line)
                if alias:
                    self.methods[alias.group(1)] = alias.group(2).strip()

            elif current_section == "compressor" and current_compressor is not None:
                if key == "header":
                    current_compressor.header = int(value)
                elif key == "solid":
                    current_compressor.solid = int(value)
                elif key == "packcmd":
                    current_compressor.packcmd = value
                elif key == "unpackcmd":
                    current_compressor.unpackcmd = value
                elif key == "datafile":
                    current_compressor.datafile = value
                elif key == "packedfile":
                    current_compressor.packedfile = value
                elif key == "default":
                    current_compressor.default = value

    def resolve_method(self, name: str) -> str:
        """
        Resuelve un alias de método, expandiendo recursivamente.
        Ej: 'xpszx' -> 'xprecomp+srep:m5f:a0+zstd:22'
        """
        visited = set()
        return self._resolve(name, visited)

    def _resolve(self, name: str, visited: set) -> str:
        if name in visited:
            return name  # Evitar recursión infinita
        visited.add(name)

        if name in self.methods:
            raw = self.methods[name]
            # Expandir cada parte de la cadena
            parts = raw.split("+")
            resolved = []
            for part in parts:
                # El nombre del compresor es la parte antes de ':'
                comp_name = part.split(":")[0]
                if comp_name in self.methods and comp_name not in visited:
                    resolved.append(self._resolve(comp_name, visited) + 
                                    (":" + ":".join(part.split(":")[1:]) if ":" in part else ""))
                else:
                    resolved.append(part)
            return "+".join(resolved)
        return name

    def get_compressor(self, name: str) -> Optional[CompressorDef]:
        return self.compressors.get(name)

    def list_methods(self) -> List[str]:
        return sorted(self.methods.keys())

    def list_compressors(self) -> List[str]:
        return sorted(self.compressors.keys())
