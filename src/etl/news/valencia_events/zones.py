"""The zone of an event: the district of València, the municipality, or "Online".

The zone is read, never looked up at run time. Everything the ETL uses was
geocoded once through the public Nominatim service in November 2026 and written
here; only answers that matched the venue, or the street and its number, were
kept. In order:

1. A venue of :data:`VENUE_ZONES` (the halls of the Palau de les Arts, the
   Filmoteca, La Rambleta, Feria Valencia...).
2. Another municipality ("Sagunt", "Aldaia", "Alcoi"): the zone is its name.
3. A street of :data:`STREET_ZONES` in the address: the street is more precise
   than a neighbourhood of the same name.
4. A district or neighbourhood name printed in the address ("El Pla del Real",
   "Ciutat Vella", "Poblados Marítimos", "Rascaña"): Meetup and Eventbrite
   locations often carry one. :data:`ZONES` maps every name, in Valencian,
   Spanish and English, to the zone it belongs to.
5. A venue the title names ("... en Roig Arena", "Concerts al MuVIM"): the
   Visit València listings print no venue, but say where the event is in the
   title. :data:`TITLE_VENUES` lists the names looked for; the record then
   carries ``metadata["zone_basis"] = "title"`` so the tab can tell it apart.

An event none of these places keeps ``""``: the tab shows it as "Sin zona"
rather than guessing. A zone is the name of a district of
València, or of one of its neighbourhoods when that is the name people use
(Ruzafa, El Carme, El Cabanyal, the villages of the outer "Poblats").
"""

import re
import unicodedata
from typing import Any

ONLINE_ZONE = "Online"
CITY_VALENCIA = "València"
NO_ZONE_LABEL = "Sin zona"

# district or neighbourhood (as it can appear in an address) → zone
ZONES: dict[str, str] = {
    # Ciutat Vella
    "ciutat vella": "Ciutat Vella",
    "ciudad vieja": "Ciutat Vella",
    "casco antiguo": "Ciutat Vella",
    "el carme": "El Carme",
    "el carmen": "El Carme",
    "la seu": "Ciutat Vella",
    "la xerea": "Ciutat Vella",
    "el pilar": "Ciutat Vella",
    "velluters": "Ciutat Vella",
    "sant francesc": "Ciutat Vella",
    "san francisco": "Ciutat Vella",
    "la barcelonina": "Ciutat Vella",
    # Eixample
    "eixample": "Eixample",
    "ensanche": "Eixample",
    "ruzafa": "Ruzafa",
    "russafa": "Ruzafa",
    "ruzzafa": "Ruzafa",
    "el pla del remei": "Eixample",
    "gran via": "Eixample",
    # Extramurs
    "extramurs": "Extramurs",
    "extramuros": "Extramurs",
    "el botanic": "Extramurs",
    "el botanico": "Extramurs",
    "la roqueta": "Extramurs",
    "la petxina": "Extramurs",
    "arrancapins": "Extramurs",
    # Campanar
    "campanar": "Campanar",
    "les tendetes": "Campanar",
    "el calvari": "Campanar",
    # La Saïdia
    "la saida": "La Saïdia",
    "la sayda": "La Saïdia",
    "marxalenes": "La Saïdia",
    "morvedre": "La Saïdia",
    "trinitat": "La Saïdia",
    "tormos": "La Saïdia",
    # El Pla del Real
    "el pla del real": "El Pla del Real",
    "el llano del real": "El Pla del Real",
    "pla del real": "El Pla del Real",
    "exposicio": "El Pla del Real",
    "exposicion": "El Pla del Real",
    "mestalla": "El Pla del Real",
    "ciutat universitaria": "El Pla del Real",
    "jaume roig": "El Pla del Real",
    # L'Olivereta
    "olivereta": "L'Olivereta",
    "nou moles": "L'Olivereta",
    "soternes": "L'Olivereta",
    "tres forques": "L'Olivereta",
    # Patraix
    "patraix": "Patraix",
    "sant isidre": "Patraix",
    "san isidro": "Patraix",
    "vara de quart": "Patraix",
    "safranar": "Patraix",
    "favara": "Patraix",
    # Jesús
    "barri de jesus": "Jesús",
    "jesus": "Jesús",
    "hort de senabre": "Jesús",
    "la raiosa": "Jesús",
    "creu coberta": "Jesús",
    "cami real": "Jesús",
    # Quatre Carreres
    "quatre carreres": "Quatre Carreres",
    "mont-oliveret": "Quatre Carreres",
    "monte olivete": "Quatre Carreres",
    "montolivet": "Quatre Carreres",
    "en corts": "Quatre Carreres",
    "malilla": "Quatre Carreres",
    "fonteta de sant lluis": "Quatre Carreres",
    "fonteta de san luis": "Quatre Carreres",
    "na rovella": "Quatre Carreres",
    "la punta": "Quatre Carreres",
    "ciutat de les arts i de les ciencies": "Quatre Carreres",
    "ciudad de las artes y de las ciencias": "Quatre Carreres",
    # Poblats Marítims
    "poblats maritims": "Poblats Marítims",
    "poblados maritimos": "Poblats Marítims",
    "el grao": "El Grao",
    "el grau de valencia": "El Grao",
    "el grao de valencia": "El Grao",
    "gra de valencia": "El Grao",
    "cabanyal": "El Cabanyal",
    "canyamelar": "El Cabanyal",
    "cabañal": "El Cabanyal",
    "cañamelar": "El Cabanyal",
    "malva-rosa": "La Malva-rosa",
    "malvarrosa": "La Malva-rosa",
    "malva rosa": "La Malva-rosa",
    "betero": "Beteró",
    "natzaret": "Natzaret",
    "nazaret": "Natzaret",
    # Camins al Grau
    "camins al grau": "Camins al Grau",
    "caminos al grao": "Camins al Grau",
    "aiora": "Camins al Grau",
    "albors": "Camins al Grau",
    "creu del grau": "Camins al Grau",
    "cami fondo": "Camins al Grau",
    # Algirós
    "algiros": "Algirós",
    "illa perduda": "Algirós",
    "ciutat jardi": "Algirós",
    "amistat": "Algirós",
    "vega baixa": "Algirós",
    "la bega baixa": "Algirós",
    "la carrasca": "Algirós",
    # Benimaclet
    "benimaclet": "Benimaclet",
    "cami de vera": "Benimaclet",
    "cami vera": "Benimaclet",
    # Rascanya
    "rascanya": "Rascanya",
    "rascania": "Rascanya",
    "rascaña": "Rascanya",
    "torrefiel": "Rascanya",
    "els orriols": "Rascanya",
    "orriols": "Rascanya",
    "sant llorenc": "Rascanya",
    "san lorenzo": "Rascanya",
    # Benicalap
    "benicalap": "Benicalap",
    "ciutat fallera": "Benicalap",
    # Poblats de l'Oest
    "poblats de l'oest": "Poblats de l'Oest",
    "poblados del oeste": "Poblats de l'Oest",
    "benimamet": "Benimàmet",
    "beniferri": "Beniferri",
    # Poblats del Sud
    "poblats del sud": "Poblats del Sud",
    "castellar": "Castellar-l'Oliveral",
    "pinedo": "Pinedo",
    "pinet": "Pinedo",
    "el saler": "El Saler",
    "el palmar": "El Palmar",
    "perellonet": "El Perellonet",
    # Poblats del Nord
    "poblats del nord": "Poblats del Nord",
    "benifaraig": "Benifaraig",
    "carpesa": "Carpesa",
    "borboto": "Poble Nou",
    "mauella": "Poble Nou",
    "massarrojos": "Poble Nou",
    "masarrojos": "Poble Nou",
    "cases de barceta": "Poble Nou",
}

# venue (as the sources print it, folded) → zone. Geocoded once in November 2026
# through the public Nominatim service; only answers that matched the venue were kept.
VENUE_ZONES: dict[str, str] = {
    "edificio rialto": "Ciutat Vella",  # Filmoteca de València, Carrer de la Barcelonina
    "teatre principal de valencia": "Ciutat Vella",  # Carrer de les Barques
    "ivam": "Ciutat Vella",  # Carrer de Guillem de Castro, El Carme
    "palau de les arts": "Quatre Carreres",
    "les arts": "Quatre Carreres",
    "sala principal": "Quatre Carreres",
    "auditori": "Quatre Carreres",
    "teatre martin i soler": "Quatre Carreres",  # codespell:ignore -- venue name
    "teatre martin i soler - palau de les arts": "Quatre Carreres",  # codespell:ignore -- venue name
    "aula magistral": "Quatre Carreres",
    "vestibul principal": "Quatre Carreres",
    "l'agora": "Quatre Carreres",  # L'Àgora, Ciutat de les Arts i de les Ciències
    "la rambleta": "Jesús",  # Plaça de Lorena Palau, Camí Real
    "teatre el musical": "El Cabanyal",  # Plaça del Rosari
    "feria valencia": "Paterna",  # Avinguda de les Fires, in the term of Paterna
    "centro cultural nau 3 ribes": "Eixample",  # Carrer de les Filipines, Parc Central
    "teatre escalante": "Ciutat Vella",  # Carrer de Landerer
    "escalante centre teatral": "Ciutat Vella",
    "cines babel": "El Pla del Real",  # Carrer de Vicent Sancho Tello, Mestalla
    "hackerspace valencia": "Benimaclet",  # Carrer de Francesc Martínez, 19
    "caixaforum": "Quatre Carreres",  # Carrer d'Eduardo Primo Yúfera, 1
    "muvim": "Ciutat Vella",  # Carrer de Quevedo, 10
    "etno": "Ciutat Vella",  # L'ETNO, Carrer de la Corona, 36
    "museo de la seda": "Ciutat Vella",  # Colegio del Arte Mayor de la Seda
    "museo de bellas artes": "La Saïdia",  # Carrer de Sant Pius V, 9 (Trinitat)
    "bombas gens": "La Saïdia",  # Calle del Velero, Marxalenes
    "centre del carme": "Ciutat Vella",  # Carrer del Museu, 2
    "hortensia herrero": "Ciutat Vella",  # Centro de Arte Hortensia Herrero, Carrer del Mar
    "jardin botanic": "Extramurs",  # Carrer de Quart, 80
    "jardin botanico": "Extramurs",
    "museu de les ciencies": "Quatre Carreres",
    "hemisferic": "Quatre Carreres",
    "oceanografic": "Quatre Carreres",
    "la marina": "Poblats Marítims",  # La Marina de València, El Grao
    "casa de la mar": "Alboraia",  # Avinguda de Vicent Blasco Ibáñez, la Vera
    "roig arena": "Quatre Carreres",  # Carrer del Bomber Ramón Duart, 12
    "sala moon": "Jesús",  # Carrer de Sant Vicent Màrtir, 200
    "sala russafa": "Ruzafa",  # Carrer de Dènia
    "teatre talia": "Ciutat Vella",  # Calle de Caballeros, 31
    "teatro talia": "Ciutat Vella",
    "teatro olympia": "Ciutat Vella",  # Carrer de Sant Vicent Màrtir, 44
    "la nau": "Ciutat Vella",  # Centre Cultural La Nau, Carrer de la Universitat, 2
    "loco club": "Extramurs",  # Carrer d'Erudit Orellana, 12, la Petxina
    "escuelas pias": "Ciutat Vella",  # Calle Carniceros
    "santos juanes": "Ciutat Vella",  # Plaça del Mercat
    "bioparc": "Campanar",  # Avinguda de Pío Baroja, Sant Pau
    "trinquet pelayo": "Extramurs",  # Carrer del Convent de Jerusalem, la Roqueta
    "estadi ciutat de valencia": "Rascanya",  # Carrer de Manuel Azaña, Sant Llorenç
    "estadio ciudad de valencia": "Rascanya",
    "mestalla": "El Pla del Real",  # Avinguda de Suècia
    "heron city": "Paterna",
    "ateneo mercantil": "Ciutat Vella",  # Plaça de l'Ajuntament
    "atenea sky": "Ciutat Vella",  # Carrer de Moratín, 12
    "palau de la musica": "El Pla del Real",  # Passeig de l'Alameda
    "palau de congressos": "Poblats de l'Oest",  # Avinguda de les Corts Valencianes, Beniferri
    "palacio de congresos": "Poblats de l'Oest",
    "cccc": "Ciutat Vella",  # Centre del Carme
    "malva-rosa": "La Malva-rosa",
    "ruzafa": "Ruzafa",
    "russafa": "Ruzafa",
    "el carme": "El Carme",
    "el carmen": "El Carme",
    "el cabanyal": "El Cabanyal",
    "el grao": "El Grao",
    "benimaclet": "Benimaclet",
    "la patacona": "Alboraia",
}

# Venue names a title can carry when the listing prints no venue ("... en Roig
# Arena", "Ciclo «Concerts al MuVIM 2026»"): folded name → the name as shown.
# Only distinctive names are listed: a common word would place an event by accident.
TITLE_VENUES: dict[str, str] = {
    "palau de les arts": "Palau de les Arts",
    "les arts": "Palau de les Arts",
    "la rambleta": "La Rambleta",
    "teatre el musical": "Teatre El Musical",
    "feria valencia": "Feria Valencia",
    "cines babel": "Cines Babel",
    "ivam": "IVAM",
    "caixaforum": "CaixaForum València",
    "muvim": "MuVIM",
    "etno": "L'ETNO",
    "museo de la seda": "Museo de la Seda",
    "museo de bellas artes": "Museo de Bellas Artes de València",
    "bombas gens": "Bombas Gens",
    "centre del carme": "Centre del Carme",
    "hortensia herrero": "Centro de Arte Hortensia Herrero",
    "jardin botanic": "Jardí Botànic",
    "jardin botanico": "Jardí Botànic",
    "museu de les ciencies": "Museu de les Ciències",
    "hemisferic": "L'Hemisfèric",
    "oceanografic": "L'Oceanogràfic",
    "la marina": "La Marina de València",
    "casa de la mar": "La Casa de la Mar",
    "roig arena": "Roig Arena",
    "sala moon": "Sala Moon",
    "sala russafa": "Sala Russafa",
    "teatre talia": "Teatre Talia",
    "teatro talia": "Teatre Talia",
    "teatro olympia": "Teatro Olympia",
    "la nau": "La Nau",
    "loco club": "Loco Club",
    "escuelas pias": "Escuelas Pías",
    "santos juanes": "Iglesia de los Santos Juanes",
    "bioparc": "Bioparc València",
    "trinquet pelayo": "Trinquet de Pelayo",
    "estadi ciutat de valencia": "Estadi Ciutat de València",
    "estadio ciudad de valencia": "Estadi Ciutat de València",
    "mestalla": "Mestalla",
    "heron city": "Heron City",
    "ateneo mercantil": "Ateneo Mercantil",
    "atenea sky": "Atenea Sky",
    "palau de la musica": "Palau de la Música",
    "palau de congressos": "Palau de Congressos",
    "palacio de congresos": "Palau de Congressos",
    "cccc": "Centre del Carme",
    "malva-rosa": "La Malva-rosa",
    "ruzafa": "Ruzafa",
    "russafa": "Ruzafa",
    "el carme": "El Carme",
    "el carmen": "El Carme",
    "el cabanyal": "El Cabanyal",
    "el grao": "El Grao",
    "benimaclet": "Benimaclet",
    "la patacona": "La Patacona",
}

# The distinctive part of a street name (folded) → zone. Geocoded once in
# November 2026; both spellings are listed where the source may use either.
STREET_ZONES: dict[str, str] = {
    "suissa": "Quatre Carreres",  # Carrer de Suïssa, la Punta
    "republica de guinea ecuatorial": "Poblats Marítims",  # Beteró
    "republica de guinea equatorial": "Poblats Marítims",
    "historiador chabas": "Ciutat Vella",
    "doctor vila barbera": "Extramurs",  # Arrancapins
    "marques de sotelo": "Ciutat Vella",
    "convent de sant francesc": "Ciutat Vella",
    "convento de san francisco": "Ciutat Vella",
    "vicent sancho tello": "El Pla del Real",  # Mestalla
    "vicente sancho tello": "El Pla del Real",
    "vall d'aiora": "Benicalap",
    "valle de ayora": "Benicalap",
    "eduardo primo yufera": "Quatre Carreres",  # Ciutat de les Arts
    "professor lopez pineiro": "Quatre Carreres",
    "profesor lopez pineiro": "Quatre Carreres",  # codespell:ignore -- Spanish
    "rodrigo botet": "Ciutat Vella",
    "d'osca": "Ciutat Vella",
    "calle huesca": "Ciutat Vella",
    "enric granados": "Patraix",
    "enrique granados": "Patraix",
    "sorni": "Eixample",  # El Pla del Remei
    "col·legi del patriarca": "Ciutat Vella",
    "colegio del patriarca": "Ciutat Vella",
    "col-legi del patriarca": "Ciutat Vella",
    "francesc martinez": "Benimaclet",
    "francisco martinez": "Benimaclet",
    "sanchis guarner": "Ruzafa",
    "landerer": "Ciutat Vella",
}

# municipality → zone shown (the name when it differs)
MUNICIPALITIES: dict[str, str] = {
    "sagunt": "Sagunt",
    "sagunto": "Sagunt",
    "puerto de sagunto": "Port de Sagunt",
    "port de sagunt": "Port de Sagunt",
    "aldaia": "Aldaia",
    "alcoi": "Alcoi",
    "alcoy": "Alcoi",
    "paterna": "Paterna",
    "burjassot": "Burjassot",
    "godella": "Godella",
    "rocafort": "Rocafort",
    "massamagrell": "Massamagrell",
    "puzol": "Puçol",
    "pucol": "Puçol",
    "el puig": "El Puig",
    "alboraia": "Alboraia",
    "alboraya": "Alboraia",
    "mislata": "Mislata",
    "quart de poblet": "Quart de Poblet",
    "manises": "Manises",
    "xirivella": "Xirivella",
    "paiporta": "Paiporta",
    "catarroja": "Catarroja",
    "silla": "Silla",
    "albal": "Albal",
    "benetusser": "Benetússer",
    "alfafar": "Alfafar",
    "sedavi": "Sedaví",
    "massanassa": "Massanassa",
    "picanya": "Picanya",
    "picassent": "Picassent",
    "foios": "Foios",
    "meliana": "Meliana",
    "vinalesa": "Vinalesa",
    "bonrepos i mirambell": "Bonrepòs i Mirambell",
    "albalat dels sorells": "Albalat dels Sorells",
    "tavernes blanques": "Tavernes Blanques",
    "torrent": "Torrent",
    "alicante": "Alacant",
    "alacant": "Alacant",
    "benifayo": "Benifaió",
    "alzira": "Alzira",
    "carcaixent": "Carcaixent",
    "cullera": "Cullera",
    "sueca": "Sueca",
    "montcada": "Montcada",
    "castello de la plana": "Castelló de la Plana",
    "castellon de la plana": "Castelló de la Plana",
    "gandia": "Gandia",
    "xativa": "Xàtiva",
    "ontinyent": "Ontinyent",
    "denia": "Dénia",
    "oliva": "Oliva",
}


def fold(text: str) -> str:
    """Lower-case text without accents or marks ("Rascanya" → "rascanya"); a typographic apostrophe becomes a plain one."""
    plain = unicodedata.normalize("NFKD", text.replace("’", "'"))
    return "".join(char for char in plain if not unicodedata.combining(char)).lower()


_VENUE_TABLE = {fold(name): zone for name, zone in VENUE_ZONES.items()}
_MUNICIPALITY_TABLE = {fold(name): zone for name, zone in MUNICIPALITIES.items()}
# Longest first, so that "teatre martin i soler - palau de les arts" is read before "palau de les arts".  # codespell:ignore -- venue name
_VENUE_NAMES = sorted(_VENUE_TABLE, key=len, reverse=True)
_STREET_NAMES = sorted(STREET_ZONES, key=len, reverse=True)
_ZONE_KEYS = sorted(ZONES, key=len, reverse=True)
_MUNICIPALITY_KEYS = sorted(_MUNICIPALITY_TABLE, key=len, reverse=True)


def _contains(folded_text: str, name: str) -> bool:
    """True when ``name`` appears in the folded text as whole words."""
    return re.search(r"(?<![a-z0-9])" + re.escape(fold(name)) + r"(?![a-z0-9])", folded_text) is not None


def _find(folded_text: str, names: list[str], table: dict[str, str]) -> str:
    """The zone of the first name of ``names`` (longest first) that the text contains."""
    for name in names:
        if _contains(folded_text, name):
            return table[name]
    return ""


def _known_venue(folded_venue: str) -> str:
    """The zone of a venue of the table, also when the text says more ("Teatre Martín i Soler - Palau de les Arts").  # codespell:ignore

    "" when the venue is not in the table, or when its text names venues of
    different zones ("Teatre Principal de València al Teatre Martín i Soler").  # codespell:ignore
    """
    exact = _VENUE_TABLE.get(folded_venue)
    if exact:
        return exact
    zones = {zone for name, zone in _VENUE_TABLE.items() if _contains(folded_venue, name)}
    return zones.pop() if len(zones) == 1 else ""


# Longest name first, so that "palau de les arts" names the venue before "les arts" does.
_TITLE_VENUES = sorted(((fold(name), shown) for name, shown in TITLE_VENUES.items()), key=lambda item: len(item[0]), reverse=True)


def venue_in_title(title: str) -> tuple[str, str]:
    """The venue a title names and its zone, read from :data:`TITLE_VENUES`.

    Returns:
        The name as shown and the zone; ``("", "")`` when the title names no
        venue of the table, or names venues in different zones.
    """
    folded = fold(title)
    found: dict[str, str] = {}
    for name, shown in _TITLE_VENUES:
        if _contains(folded, name):
            found.setdefault(_VENUE_TABLE[name], shown)
    if len(found) != 1:
        return "", ""
    zone, shown = found.popitem()
    return shown, zone


def zone_of(*, venue: str = "", address: str = "", location: str = "", city: str = "", online: bool = False) -> str:
    """The zone of an event, or "" when nothing tells it.

    Args:
        venue: Venue name as the source prints it.
        address: Address text.
        location: The location text the JSON-LD sources carry ("street, district, city").
        city: Municipality when the source states it.
        online: True for an event held online.

    Returns:
        "Online", a district or village of València, another municipality, or "".
    """
    if online:
        return ONLINE_ZONE
    zone = _known_venue(fold(venue))
    if zone:
        return zone
    said_city = (city or "").strip()
    folded_city = fold(said_city)
    if folded_city and folded_city != "valencia":
        return _MUNICIPALITY_TABLE.get(folded_city) or said_city
    text = fold(f"{address} {location}")
    zone = _find(text, _STREET_NAMES, STREET_ZONES) or _find(text, _ZONE_KEYS, ZONES) or _find(text, _MUNICIPALITY_KEYS, _MUNICIPALITY_TABLE)
    return zone


def zone_label(zone: str | None) -> str:
    """Text shown for a zone: the zone itself, or "Sin zona" for an empty one."""
    return zone or NO_ZONE_LABEL


def zones_of(events: list[dict[str, Any]]) -> list[str]:
    """The distinct zones of a list of normalised events, sorted; "" is one of them when present."""
    return sorted({str(event.get("zone") or "") for event in events})
