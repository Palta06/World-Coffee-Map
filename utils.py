import unicodedata
import re

def strip_accents(s: str) -> str:
    if not isinstance(s, str):
        return s
    nfkd = unicodedata.normalize('NFKD', s)
    return ''.join([c for c in nfkd if not unicodedata.combining(c)])

def normalize_name_for_match(s: str) -> str:
    """Normaliza un nombre quitando acentos, paréntesis, artículos comunes, puntuación y lowercasing."""
    if not isinstance(s, str):
        return ""
    s = s.strip()
    s = re.sub(r'\(.*?\)', '', s)                
    s = strip_accents(s)                        
    s = s.replace('&', 'and')
    s = s.replace('-', ' ')
    s = s.replace('/', ' ')
    s = re.sub(r'[^0-9A-Za-z\s]', '', s)         
    s = re.sub(r'\s+', ' ', s)                  
    return s.strip().lower()

def detect_year_columns(columns) -> list:
    """Detecta columnas que parezcan años (1990, 1990/91, 1990-91, etc.)"""
    year_regex = re.compile(r'^\s*\d{4}(\s*[-/]\s*\d{2,4})?\s*$')
    return [c for c in columns if isinstance(c, str) and year_regex.match(c.strip())]

def year_label_to_int(label: str) -> int:
    """Extrae el año inicial como entero para ordenar: '1990/91'->1990, '1990'->1990"""
    if not isinstance(label, str):
        return 9999
    m = re.match(r'^\s*(\d{4})', label)
    return int(m.group(1)) if m else 9999