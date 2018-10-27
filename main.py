import requests
import time
import os
import settings
import justext
from ebooklib import epub
from jinja2 import Environment, FileSystemLoader
from geopy.geocoders import Nominatim
from newspaper import Article
from docutils.core import publish_doctree, publish_from_doctree
from bs4 import BeautifulSoup
from custom_filters import TemplateFilters

class NewsEbookCreator:

    DARK_SKY_API_URL = "https://api.darksky.net/forecast/{}/{},{}"
    NEWS_API_URL = "https://newsapi.org/v2/top-headlines"
    MAILGUN_API_URL = "https://api.mailgun.net/v3/{}/messages"

    EPUB_META_AUTHOR = "News eBook Creator"
    EPUB_META_TIILE = 'News Update (%m/%d/%y, %I:%M%p)'
    EPUB_META_LANG = "en"

    def __init__(self, city: str, to_email: list, delete_after: bool = False):
        self.city = city
        self.to_email = to_email
        self.delete_after = delete_after

        self.env = Environment(loader=FileSystemLoader(os.getcwd()))
        TemplateFilters.register_template_filters_to_env(self.env)

        self.book = epub.EpubBook()

        self.book_filename = time.strftime(self.EPUB_META_TIILE)
        self.target_time = int(round(time.time()))

        self.book.set_identifier('ebook_news_{}'.format(self.target_time))
        self.book.set_title(self.book_filename)
        self.book.set_language(self.EPUB_META_LANG)
        self.book.add_author(self.EPUB_META_AUTHOR)

        self.chaps = []
        self.toc_list = []

    def get_and_ebookize_weather(self):
        # use template
        template = self.env.get_template('weather_template.html')

        # Geo-locate
        geolocator = Nominatim(user_agent=settings.NOMINATIM_USER_AGENT)
        location = geolocator.geocode(self.city)
        r = requests.get(self.DARK_SKY_API_URL.format(settings.DARK_SKY_API_KEY, location.latitude, location.longitude))
        # TODO: Error-check request.

        # put into book
        c = epub.EpubHtml(title="weather", file_name="weather.xhtml", lang='en')
        c.set_content(template.render(weather=r.json()))
        self.book.add_item(c)
        self.chaps.append(c)
        self.weather_link = epub.Link("weather.xhtml", "Current Weather", "weather00")

    def get_and_ebookize_news(self):
        all_articles = self._download_all_news()
        self._ebookize_all_news(all_articles)

    def _download_all_news(self):
        # download and parse news
        r = requests.get(self.NEWS_API_URL, params={'apiKey': settings.NEWS_API_KEY, 'country': "us"})
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

        return parsed_articles

    def _ebookize_all_news(self, parsed_articles):
        template = self.env.get_template('article_template.html')
        self.article_toc_list = []

        for a in parsed_articles:

            if a["top_image"] is not None:
                img_file_name = "art_img/image_{:03d}".format(a["count"])
                epimg = epub.EpubImage()
                epimg.file_name = img_file_name
                epimg.media_type = "image/jpeg"
                img_resp = requests.get(a["top_image"])
                img = img_resp.content
                epimg.set_content(img)
                self.book.add_item(epimg)

                a["top_image"] = img_file_name

            c = epub.EpubHtml(title=a["title"], file_name="article_{}.xhtml".format(a["count"]), lang='en')
            tree = publish_doctree(a["article_text"])
            html = publish_from_doctree(tree, writer_name='html').decode()
            soup = BeautifulSoup(html, 'lxml')
            body_only = soup.find('body').find('div', {"class": "document"})

            # skip articles that have barred keywords
            if any(kw in a["title"].lower() for kw in settings.TITLE_EXCLUSIONS):
                continue

            if len(body_only.findAll('p')) < settings.MIN_PARAGRAPHS_FOR_AN_ARTICLE:
                # fall back to justext to synthesize article
                a["article_text"] = ""
                count = 0
                paragraphs = justext.justext(requests.get(a["url"]).content, justext.get_stoplist("English"))
                for paragraph in paragraphs:
                    if not paragraph.is_boilerplate:
                        count += 1
                        a["article_text"] += "<p>{}</p>".format(paragraph.text)
                if count < settings.MIN_PARAGRAPHS_FOR_AN_ARTICLE:
                    continue  # if it's still short, then it's actually short and not parsed incorrectly...continue
                else:
                    pass
                    # article as indeed parsed incorrectly TODO: Print statements
            else:
                a["article_text"] = body_only

            c.set_content(template.render(article=a))
            self.chaps.append(c)
            self.book.add_item(c)
            self.article_toc_list.append(
                epub.Link("article_{}.xhtml".format(a["count"]), "{} - {}".format(a["title"], a["source"]),
                          "art%d" % a["count"]))

    def bind_and_save_epub(self):
        self.book.toc = (self.weather_link,
                         (epub.Section("Articles"), tuple(self.article_toc_list))
                         )

        # add navigation files
        self.book.add_item(epub.EpubNcx())
        self.book.add_item(epub.EpubNav())

        # define css style
        with open('book_style.css', 'r') as css_file:
            style = css_file.read()

        # add css file
        nav_css = epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", content=style)
        self.book.add_item(nav_css)

        self.chaps.insert(0, 'nav')
        self.book.spine = self.chaps

        self.book_filename = 'news_update_{}.epub'.format(self.target_time)
        epub.write_epub(self.book_filename, self.book, {})

    def email_ebook(self):
        URL = self.MAILGUN_API_URL.format(settings.MAILGUN_DOMAIN)
        r = requests.post(
            URL,
            auth=("api", settings.MAILGUN_API_KEY),
            files=[("attachment", open(self.book_filename, "rb"))],
            data={
                "subject": "News Update ({})".format(TemplateFilters.secToStrfTime(int(self.target_time))),
                "from": settings.MAILGUN_FROM_ADDR,
                "to": self.to_email,
                "text": "Your news update for {}.".format(TemplateFilters.secToStrfTime(int(self.target_time))),
                "html": "<p>Your news update for {}.<p>".format(TemplateFilters.secToStrfTime(int(self.target_time))),
            }
        )
        # TODO: Check for errors
        print(r.text)