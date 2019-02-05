# News eBook Creator

This is a script that turns the latest news into an e-book and emails it to you.

It uses:
* [News API](https://newsapi.org/) to get the latest headlines,
* [Dark Sky's API](https://darksky.net/dev) to get weather information, and
* [Mailgun](https://www.mailgun.com/) to send the email.

## Screenshots (as viewed in Calibre's e-book viewer)

_Table of contents_

![News e-book table of contents](https://vnair.me/images/hotlink-ok/news-ebook/00-toc.png)

_Weather information_

![News e-book weather information](https://vnair.me/images/hotlink-ok/news-ebook/01-weather.png)

_News article_

![News e-book article](https://vnair.me/images/hotlink-ok/news-ebook/02-article.png)

## Usage

```
usage: main.py [-h] -c CITY -e EMAIL [EMAIL ...] [-d]

Create an EPUB-formatted eBook with the latest weather and news headlines.

optional arguments:
  -h, --help            show this help message and exit
  -c CITY, --city CITY  <REQUIRED> city whose weather to download
  -e EMAIL [EMAIL ...], --email EMAIL [EMAIL ...]
                        <REQUIRED> emails to send the resultant ebook to
  -d, --delete          <OPTIONAL> delete the saved ebook from the filesystem
                        (default [without this arg]: keeps the book)
```

### Settings

Some settings need to be set in `settings.py` before the first use. They should be self-explanatory.

```
# KEYS AND IDENTIFIERS
DARK_SKY_API_KEY = ""
NEWS_API_KEY = ""
MAILGUN_API_KEY = ""
NOMINATIM_USER_AGENT = ""   # Unique user-agent string for identification to the Nominatim server.

# MAIL
MAILGUN_DOMAIN = ""         # The domain under which the Mailgun account is registered.
MAILGUN_FROM_ADDR = ""      # The address from which emails should be sent (preferably of the form "From Name <something@example.com>"
```
