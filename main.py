import requests
import time
import os
import settings
from ebooklib import epub
from jinja2 import Environment, FileSystemLoader
from geopy.geocoders import Nominatim
from newspaper import Article
from docutils.core import publish_doctree, publish_from_doctree
from bs4 import BeautifulSoup


DARK_SKY_API_URL = "https://api.darksky.net/forecast/{}/{},{}"
NEWS_API_URL = "https://newsapi.org/v2/top-headlines"

book = epub.EpubBook()
chaps = []

env = Environment(loader=FileSystemLoader(os.getcwd()))

book.set_identifier('ebook_news_{}'.format(int(round(time.time()))))
book.set_title("News Update (10/22/18, 7:30pm)")
book.set_language("en")
book.add_author("News eBook Creator")

# get weather
geolocator = Nominatim(user_agent="")
location = geolocator.geocode("New York, NY")
r = requests.get(DARK_SKY_API_URL.format(settings.DARK_SKY_API_KEY, location.latitude, location.longitude))
# TODO: Error-check request.

# use template
template = env.get_template('weather_template.html')
c = epub.EpubHtml(title="weather", file_name="weather.xhtml", lang='en')
c.set_content(template.render(weather=r.json()))
book.add_item(c)
chaps.append(c)
weather_link = epub.Link("weather.xhtml", "Current Weather", "weather00")

# news
r = requests.get(NEWS_API_URL, params={'apiKey': settings.NEWS_API_KEY, 'country': "us"})
# TODO: Error-check request.
news_request_results = r.json()
parsed_articles = []
count = 0

for a in news_request_results["articles"]:
    pa = {
        "count": count,
        "source": a["source"]["name"],
        "author": a["author"],
        "title": a["title"],
        "top_image": a["urlToImage"],
        "desc": a["description"],
        "url": a["url"]
    }
    this_article = Article(pa["url"])
    this_article.download()
    this_article.parse()
    pa["article_text"] = this_article.text
    count += 1
    parsed_articles.append(pa)

# use template
template = env.get_template('article_template.html')
article_toc_list = []

for a in parsed_articles:
    # TODO: Consider applying top/main image.

    c = epub.EpubHtml(title=a["title"], file_name="article_{}.xhtml".format(a["count"]), lang='en')
    tree = publish_doctree(a["article_text"])
    html = publish_from_doctree(tree, writer_name='html').decode()
    soup = BeautifulSoup(html, 'lxml')
    body = soup.find('body').find('div', {"class": "document"})
    a["article_text"] = body

    c.set_content(template.render(article=a))
    chaps.append(c)
    book.add_item(c)

    article_toc_list.append(
        epub.Link("article_{}.xhtml".format(a["count"]), "{} - {}".format(a["title"], a["source"]),
                  "art%d" % a["count"]))

book.toc = (weather_link,
            (epub.Section("Articles"), tuple(article_toc_list))
            )

# add navigation files
book.add_item(epub.EpubNcx())
book.add_item(epub.EpubNav())

# define css style
with open('book_style.css', 'r') as css_file:
    style = css_file.read()

# add css file
nav_css = epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", content=style)
book.add_item(nav_css)