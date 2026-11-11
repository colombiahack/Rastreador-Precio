from .falabella import Falabella
from .jsonld import Alkosto, Ktronix
from .mercadolibre import MercadoLibre
from .vtex import Exito, Olimpica

SCRAPERS = {
    "exito": Exito,
    "olimpica": Olimpica,
    "mercadolibre": MercadoLibre,
    "falabella": Falabella,
    "alkosto": Alkosto,
    "ktronix": Ktronix,
}
