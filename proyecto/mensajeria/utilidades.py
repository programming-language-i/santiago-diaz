"""Utilidades puras y funciones auxiliares para el sistema de mensajería."""

from datetime import datetime, timezone
import re

# Stopwords en español para filtrado de reportes
STOPWORDS_ESPANOL = frozenset({
    "de", "la", "que", "el", "en", "y", "a", "los", "del", "se", "las", "por",
    "un", "para", "con", "no", "una", "su", "al", "lo", "como", "mas", "más",
    "pero", "sus", "le", "ya", "o", "este", "si", "sí", "porque", "esta",
    "son", "entre", "cuando", "muy", "sin", "sobre", "ser", "tiene",
    "tambien", "también", "me", "hasta", "hay", "donde", "quien", "desde",
    "todo", "nos", "durante", "todos", "uno", "les", "ni", "contra", "otros",
    "ese", "eso", "ante", "ellos", "e", "esto", "mi", "antes", "algunos",
    "unos", "yo", "otro", "otras", "otra", "ella", "ello"
})

_PATRON_PALABRA = re.compile(r"\b[a-zA-ZáéíóúÁÉÍÓÚñÑ0-9_]{3,}\b")

# Funciones puras usando lambdas donde es directo
obtener_timestamp_iso = lambda: datetime.now(timezone.utc).isoformat()


def formatear_hora_corta(iso_timestamp: str) -> str:
    """Convierte ISO-8601 a HH:MM:SS."""
    try:
        return datetime.fromisoformat(iso_timestamp).strftime("%H:%M:%S")
    except ValueError:
        return iso_timestamp


def extraer_hora_del_dia(iso_timestamp: str) -> int:
    """Extrae hora (0-23) de ISO-8601. Retorna -1 si es inválido."""
    try:
        return datetime.fromisoformat(iso_timestamp).hour
    except ValueError:
        return -1


def tokenizar_palabras(texto: str) -> list[str]:
    """Extrae palabras relevantes (>=3 chars, sin stopwords) en minúsculas."""
    # Declarativo: filter + lambda para excluir stopwords
    palabras = _PATRON_PALABRA.findall(texto.lower())
    return list(filter(lambda p: p not in STOPWORDS_ESPANOL, palabras))
