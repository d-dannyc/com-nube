"""Extracción de texto DOCX con límites; no ejecuta macros ni carga recursos externos."""
import io
from pathlib import Path
import zipfile
import zlib
from xml.etree import ElementTree as ET

MAX_DOCX_BYTES = 16 * 1024 * 1024
MAX_XML_BYTES = 4 * 1024 * 1024
MAX_TEXT_BYTES = 512 * 1024


def texto_docx(nombre: str, contenido: bytes) -> str | None:
    if Path(nombre).suffix.lower() != '.docx' or len(contenido) > MAX_DOCX_BYTES:
        return None
    try:
        with zipfile.ZipFile(io.BytesIO(contenido)) as archive:
            info = archive.getinfo('word/document.xml')
            if info.file_size > MAX_XML_BYTES:
                return None
            with archive.open(info) as part:
                xml = part.read(MAX_XML_BYTES + 1)
        if len(xml) > MAX_XML_BYTES or b'<!DOCTYPE' in xml.replace(b'\0', b'').upper():
            return None
        body = ET.fromstring(xml).find('.//{*}body')
        if body is None:
            return None
        def inline(node):
            tag = node.tag.rsplit('}', 1)[-1]
            if tag in {'del', 'moveFrom', 'drawing', 'pict', 'object'}:
                return ''
            if tag == 't':
                return node.text or ''
            if tag == 'tab':
                return '\t'
            if tag in {'br', 'cr'}:
                return '\n'
            return ''.join(inline(child) for child in node)

        def blocks(node):
            for child in node:
                tag = child.tag.rsplit('}', 1)[-1]
                if tag == 'p':
                    yield inline(child)
                elif tag == 'tbl':
                    for row in child.findall('./{*}tr'):
                        yield '\t'.join('\n'.join(blocks(cell)) for cell in row.findall('./{*}tc'))
                elif tag not in {'del', 'moveFrom', 'sectPr'}:
                    yield from blocks(child)
        text = '\n'.join(blocks(body))
        return text if len(text.encode('utf-8')) <= MAX_TEXT_BYTES else None
    except (zipfile.BadZipFile, KeyError, ET.ParseError, RuntimeError, OSError, ValueError, RecursionError, zlib.error):
        return None
