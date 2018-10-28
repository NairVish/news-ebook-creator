import requests
import settings
import os
import sys
import time
import argparse
import justext
from bs4 import BeautifulSoup
from geopy.geocoders import Nominatim
from newspaper import Article
from ebooklib import epub
from docutils.core import publish_doctree, publish_from_doctree
from jinja2 import Environment, FileSystemLoader
from custom_filters import TemplateFilters


class NewsEbookCreator:
    """
    Handles synthesis of an ebook that contains the latest news headlines and weather,
    """

    EPUB_META_AUTHOR = "News eBook Creator"
    EPUB_META_TIILE = 'News Update (%m/%d/%y, %I:%M%p)'
    EPUB_META_LANG = "en"

    DARK_SKY_API_URL = "https://api.darksky.net/forecast/{}/{},{}"
    NEWS_API_URL = "https://newsapi.org/v2/top-headlines"
    MAILGUN_API_URL = "https://api.mailgun.net/v3/{}/messages"

    def __init__(self, city: str, to_email: list, delete_after: bool = False):
        """
        Initializes and prepares the class.
        :param city: The city whose weather to download and add to the ebook.
        :param to_email: The email(s) to send the ebook to.
        :param delete_after: Whether or not to delete the synthesized ebook after the script finishes.
        """
        # Handle parameters
        self.city = city
        self.to_email = to_email
        self.delete_after = delete_after

        # Instantiate Jinja2 environment.
        self.env = Environment(loader=FileSystemLoader(os.getcwd()))
        TemplateFilters.register_template_filters_to_env(self.env)

        # Instantiate ebook.
        self.book = epub.EpubBook()

        # Set ebook metadata
        self.book_filename = time.strftime(self.EPUB_META_TIILE)
        self.target_time = int(round(time.time()))

        self.book.set_identifier('ebook_news_{}'.format(self.target_time))
        self.book.set_title(self.book_filename)
        self.book.set_language(self.EPUB_META_LANG)
        self.book.add_author(self.EPUB_META_AUTHOR)

        self.chaps = []
        self.toc_list = []

    def synthesize_ebook(self):
        """
        Run through synthesis of the ebook.
        """
        print("===== SYNTHESIZING EBOOK =====")
        self.get_and_ebookize_weather()
        self.get_and_ebookize_news()
        self.bind_and_save_epub()
        self.email_ebook()
        if self.delete_after:
            self.delete_ebook_file()
        print("===== SYNTHESIS DONE =====")

    def get_and_ebookize_weather(self):
        """
        Downloads and parses weather data and then adds it to the ebook.
        """
        print("=== Getting and ebook-izing weather. ===")
        # get template
        template = self.env.get_template('weather_template.html')

        # Geo-locate
        geolocator = Nominatim(user_agent=settings.NOMINATIM_USER_AGENT)
        location = geolocator.geocode(self.city)
        r = requests.get(self.DARK_SKY_API_URL.format(settings.DARK_SKY_API_KEY, location.latitude, location.longitude))
        if r.status_code != 200:
            print("Dark Sky's response: {}".format(r.text))
            r.raise_for_status()
        print("Downloaded weather.")

        # put into book
        c = epub.EpubHtml(title="weather", file_name="weather.xhtml", lang='en')
        c.set_content(template.render(weather=r.json()))
        self.book.add_item(c)
        self.chaps.append(c)
        self.weather_link = epub.Link("weather.xhtml", "Current Weather", "weather00")

    def get_and_ebookize_news(self):
        """
        Downloads and parses news data and then adds it to the ebook.
        """
        print("=== Getting and processing news. ===")
        all_articles = self._download_all_news()
        self._ebookize_all_news(all_articles)

    def _download_all_news(self):
        """
        Downloads and processes all news data for subsequent addition to the ebook.
        :return: A list of dicts of parsed articles.
        """
        print("* Downloading top headlines as of this moment. *")
        # download and parse news
        r = requests.get(self.NEWS_API_URL, params={'apiKey': settings.NEWS_API_KEY, 'country': "us"})
        if r.status_code != 200:
            print("News API's response: {}".format(r.text))
            r.raise_for_status()
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
            print("Downloaded and parsed #{}: {}".format(count, pa["title"]))
            count += 1
            parsed_articles.append(pa)

        return parsed_articles

    def _ebookize_all_news(self, parsed_articles):
        """
        Adds the previously processed news data to the ebook.
        :param parsed_articles: The previously processed news data.
        """
        print("* Ebook-izing downloaded headlines. *")
        # some initialization
        template = self.env.get_template('article_template.html')
        self.article_toc_list = []

        # put each into ebook
        for a in parsed_articles:
            print("Loading #{} into ebook: {}".format(a["count"], a["title"]))

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
                print("\tArticle title contains a barred keyword. Skipping.")
                continue

            if len(body_only.findAll('p')) < settings.MIN_PARAGRAPHS_FOR_AN_ARTICLE:
                print(
                    "\tArticle from {} too short. It may be paywalled or a video. It may also have been parsed incorrectly."
                    "\n\tURL: {}".format(a["source"], a["url"]))
                # fall back to justext to synthesize article
                a["article_text"] = ""
                count = 0
                paragraphs = justext.justext(requests.get(a["url"]).content, justext.get_stoplist("English"))
                for paragraph in paragraphs:
                    if not paragraph.is_boilerplate:
                        count += 1
                        a["article_text"] += "<p>{}</p>".format(paragraph.text)
                if count < settings.MIN_PARAGRAPHS_FOR_AN_ARTICLE:
                    print("\t\tArticle parsed correctly but actually short. Skipping.")
                    continue  # if it's still short, then it's actually short and not parsed incorrectly...continue
                else:
                    print("\t\tArticle was indeed parsed incorrectly. Fallback has parsed it correctly.")
            else:
                a["article_text"] = body_only

            c.set_content(template.render(article=a))
            self.chaps.append(c)
            self.book.add_item(c)
            self.article_toc_list.append(
                epub.Link("article_{}.xhtml".format(a["count"]), "{} - {}".format(a["title"], a["source"]),
                          "art%d" % a["count"]))

    def bind_and_save_epub(self):
        """
        Finalizes binding of the ebook and saves it to the filesystem.
        """
        print("=== Binding and saving EPUB. ===")
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
        print("Saved as {}.".format(self.book_filename))

    def email_ebook(self):
        """
        Emails the ebook to the designated recipients.
        """
        print("=== Emailing book. ===")
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
        print("Mailgun's response:\n{}".format(r.text))
        r.raise_for_status()

    def delete_ebook_file(self):
        """
        Deletes the synthesized ebook file from the filesystem.
        :return:
        """
        print("=== Deleting ebook file. ===")
        os.remove(self.book_filename)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create an EPUB-formatted eBook with the latest weather and news headlines.")
    parser.add_argument("-c", "--city", required=True, help="<REQUIRED> city whose weather to download")
    parser.add_argument("-e", "--email", nargs='+', required=True,
                        help="<REQUIRED> emails to send the resultant ebook to")
    parser.add_argument("-d", "--delete", action="store_true", default=False,
                        help="<OPTIONAL> delete the saved ebook from the filesystem (default [without this arg]: keeps the book)")

    # if no arguments are given, automatically print the help text (-h option)
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = vars(parser.parse_args())
    print("Arguments: {}".format(args))
    new_ebook = NewsEbookCreator(args["city"], args["email"], delete_after=args["delete"])
    new_ebook.synthesize_ebook()
