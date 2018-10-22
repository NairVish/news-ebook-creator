import requests
import time
import settings
from ebooklib import epub
from geopy.geocoders import Nominatim

DARK_SKY_API_URL = "https://api.darksky.net/forecast/{}/{},{}"
NEWS_API_URL = "https://newsapi.org/v2/top-headlines"

book = epub.EpubBook()

book.set_identifier('ebook_news_{}'.format(int(round(time.time()))))
book.set_title("News Update (10/22/18, 7:30pm)")
book.set_language("en")
book.add_author("News eBook Creator")

# get weather
geolocator = Nominatim(user_agent="")
location = geolocator.geocode("New York, NY")
r = requests.get(DARK_SKY_API_URL.format(settings.DARK_SKY_API_KEY, location.latitude, location.longitude))
# TODO: Error-check request.