"""The categories of Valencia events: one vocabulary, and how a record gets one.

A source that names the kind of an event is believed: the Ayuntamiento prints
its category, Les Arts and La Rambleta their own, an event of the Meetup Tech
category is ``tech``. The legacy sources only carry hints (``exposición``,
``tecnología``, ``meetup``) or nothing, and the Visit València listings name no
category at all: those are inferred from the title, then from the description,
with the first rule of :data:`RULES` that matches. A record nothing says
anything about takes the default of its source (``metadata["default_category"]``)
or ``otro``.

"Gratuito" is not a category: whether an event is free is a price fact
(``price == 0``), kept apart so that "solo gratis" combines with any category.
"""

import re
import unicodedata
from collections.abc import Mapping
from typing import Any

CATEGORIES: tuple[str, ...] = ("música", "teatro", "humor", "danza", "cine", "arte", "tech", "ferias", "infantil", "deporte", "fiestas", "gastronomía", "charlas y talleres", "visitas y rutas", "otro")
UNKNOWN_CATEGORY = "otro"

# Category values the legacy sources emit (the keyword pass of ``process_valencia_events``).
# A value missing here (``meetup``, ``eventbrite``, ``festival``, ``cultura``) says nothing: infer.
HINT_MAP: dict[str, str] = {
    "exposición": "arte",
    "música": "música",
    "concierto": "música",
    "gastronomía": "gastronomía",
    "espectáculo": "teatro",
    "deporte": "deporte",
    "naturaleza": "visitas y rutas",
    "fiestas": "fiestas",
    "arte": "arte",
    "literatura": "charlas y talleres",
    "educación": "charlas y talleres",
    "tecnología": "tech",
    "conferencia": "charlas y talleres",
    "taller": "charlas y talleres",
}

# Listings mix Spanish, Valencian and English; texts are folded to plain lower-case
# ASCII before matching (see ``fold``), so every pattern here is accent-free.
_PATTERNS: dict[str, str] = {
    "tech": r"\b(tech\b|tecnolog|software|programador|programmers?|developer|devops|python|javascript|typescript|golang|kubernetes|cloud|ai\b|inteligencia artificial|llm|startup|hackathon|data (engineer|science|analytics)|big data|cybersecurity|ciberseguridad|java\b|react\b|node\b|aws\b|gcp\b|azure\b|coders?\b|coding|linux|arduino|raspberry|blockchain|web3|machine learning|makers?\b|impresion 3d|apis?\b|sql\b|agile\b|scrum|kanban|product (manager|management)|user experience|ux\b|ui\b|design (thinking|sprint)|serverless|docker|open source|codigo|iot\b|robot|dron|automatizacion|dev\b|backend|frontend|full ?stack|low ?code|no ?code|digital (business|marketing|transformation|expo))",
    "cine": r"\b(cine|proyeccion|pelicula|film|documental|cortometraje|seminci|cineforum|audiovisual)",
    "danza": r"\b(ballet|danza|dansa|danses|dancers?|ball de|balls al carrer|coreograf|folclor|folklor)",
    "humor": r"\b(humor|stand-?up|monolog|clown|payas|magia|mago|magica|comico|comica|comediante|absurdo)",
    "música": r"\b(conciert|concerts?\b|recital|orquest|sinfon|opera|jazz|flamenco|dj\b|djs\b|camerata|cantautor|cuarteto|quinteto|soul|funk|reggae|techno|hip-?hop|rap\b|rock\b|pop\b|blues|bossa|bolero|zarzuela|berklee|ensemble (nights?|concert)|orchestra|songs?\b|singer|songwriter|actua\b|en directo|disc jockey|bandas sonoras|solista|cantante|cantant|coro\b|coral\b|orfeo\b|violinchelo|cello|violin|piano|guitarra|guitar|tributo|tribute|banda de musica)",
    "teatro": r"\b(teatro|teatre|comedia|drama|tragedia|musical|circo|titere|marioneta|espectac|show\b|gira\b|teatral)",
    "arte": r"\b(exposicion|muestra|galeria|pintura|escultura|fotografia|museo|museum|ivam|coleccion|col·leccio|instalacion|grabado|arte\b|artista|diseno|ilustracion|acuarela|ceramica|dibujo|bombas gens|hortensia herrero|muvim|caixaforum|centre del carme|pinacoteca)",
    "gastronomía": r"\b(gastronom|cocina|tapas|paella|degustacion|degusta|vinos?\b|vinedos|enotur|cerveza|gastro|chef|cocas|gourmet|restaurant|helado|chocolate|culinario|reposteria|vermut|cata\b|cena\b|horchata|orxata|maridaje|clochina|brunch)",
    "deporte": r"\b(10k|42k|maraton|partido|baloncesto|futbol|tenis|padel|ciclismo|triatlon|regata|volley|voleibol|motogp|formula|campeonato|trofeo|running|carrera popular|carrera nocturna|carrera urbana|corriendo|san silvestre|yoga|pilates|meditacion|tournament|torneo|atletismo|pilota|mestalla|estadio|circuit|golf|valencia cf|valencia basket|basket\b|skate|escalada|patinaje|kms?\b)",
    "infantil": r"\b(infantil|familiares|familiar|familia\b|ninos?\b|ninas?\b|bebes|peques|cuentacuentos|cuentos?\b|ludoteca|menores de)",
    "ferias": r"\b(feria|fira|salon|congreso|convenio|expo|summit|convencion|job fair)",  # codespell:ignore -- Spanish
    "fiestas": r"\b(fiesta|verbena|navidad|naviden|fallas?\b|nit de sant joan|noche de san juan|foguer|corpus|moros y cristianos|semana santa|nochevieja|ano nuevo|reyes|carnaval|halloween|disco|party|cumpleanos|social|language exchange|intercambio de idiomas)",
    "visitas y rutas": r"\b(visita|guiad|ruta|rutas|paseo|walks?\b|recorrido|excursion|tour|itinerario|monumento|catedral|torres|albufera|huerta|naturaleza|senderismo|bicicleta|en bici|patrimonio|cuevas|iglesia|basilica|convento|palacio|turistic|inmersiv|interpretacion|interpretacio|barraca|alqueria)",
    "charlas y talleres": r"\b(taller|workshop|curso|formacion|conferenc|charla|seminario|jornada|jornades|coloquio|debate|ponencia|presentacion|encuentro|masterclass|webinar|talk|meetup|networking|dialogo|lectura|book club|poesia|literatura|premio|philosoph|filosof|founders|empren)",
}

# In order of precedence: the first rule whose pattern matches wins.
RULE_ORDER: tuple[str, ...] = ("tech", "cine", "danza", "humor", "música", "teatro", "arte", "gastronomía", "deporte", "infantil", "ferias", "fiestas", "visitas y rutas", "charlas y talleres")
RULES: tuple[tuple[str, re.Pattern[str]], ...] = tuple((category, re.compile(_PATTERNS[category])) for category in RULE_ORDER)

# Meetup groups of València whose events are technology by nature.
TECH_GROUPS: frozenset[str] = frozenset(
    {
        "valencia-codes",
        "gdg-valencia",
        "valenciajs",
        "python-valencia",
        "cloud-native-valencia",
        "ai-tinkerers-valencia",
        "hackerspace-valencia",
        "agile-valencia",
        "valencia-jug",
        "valencia-devops",
        "aws-valencia",
        "valencia-data",
        "valencia-ai",
    }
)


def fold(text: str) -> str:
    """Lower-case text without accents or other marks ("Música" → "musica")."""
    return "".join(char for char in unicodedata.normalize("NFKD", text) if not unicodedata.combining(char)).lower()


# The hints folded: the lookup folds what the source said.
_HINT_TABLE: dict[str, str] = {fold(hint): category for hint, category in HINT_MAP.items()}


def infer_category(title: str, description: str = "") -> str:
    """Category the words of a title (then of a description) suggest; "" when none does."""
    for text in (title, description):
        folded = fold(text)
        for category, pattern in RULES:
            if pattern.search(folded):
                return category
    return ""


def meetup_group(url: str) -> str:
    """Group slug of a Meetup event link (``valencia-codes``); "" for any other link."""
    match = re.search(r"meetup\.com/([^/?#]+)/events/", url or "")
    return match.group(1).lower() if match else ""


def normalise_category(category: str, title: str, description: str = "", *, default_category: str = "", url: str = "") -> str:
    """The one category a record gets.

    Args:
        category: What the source said: a vocabulary value, a legacy hint, or "".
        title: Event title.
        description: Event description.
        default_category: Category of the source when nothing else is known.
        url: Event link; a technology meetup is ``tech`` whatever its title.

    Returns:
        A value of :data:`CATEGORIES`.
    """
    said = (category or "").strip()
    if said in CATEGORIES:
        return said
    hint = _HINT_TABLE.get(fold(said))
    if hint:
        return hint
    if meetup_group(url) in TECH_GROUPS:
        return "tech"
    inferred = infer_category(title, description)
    if inferred:
        return inferred
    if default_category in CATEGORIES:
        return default_category
    return UNKNOWN_CATEGORY
