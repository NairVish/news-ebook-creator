import requests
import time
from ebooklib import epub

book = epub.EpubBook()

book.set_identifier('ebook_news_{}'.format(int(round(time.time()))))
book.set_title("News Update (10/22/18, 7:30pm)")
book.set_language("en")
book.add_author("News eBook Creator")