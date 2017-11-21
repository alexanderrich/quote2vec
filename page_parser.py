from bs4 import BeautifulSoup
import re
import langdetect
import langid


def parse_html(html):
    """Takes html string of a wikiquote page and returns a list of quotes

    Args:
        html (str): full html string of a wikiquote
        page, as scraped using api.

    Returns:
        list or None: list of found quotes, or None
        if the article requires cleanup.

    """
    cleanupstring = "https://en.wikipedia.org/wiki/Wikipedia:Cleanup"
    if cleanupstring in html:
        return None
    soup = BeautifulSoup(html, 'html.parser')
    soup = soup.contents[0]
    node = parse_to_quotes(soup.contents[0])
    quotes = []
    # quotes under these titles likely aren't actually by the individual
    blacklist = ['Disputed', 'Attributed',
                 'Misattributed', 'Quotes about',
                 'Quotations about',
                 'Quotations regarding', 'See also', 'References',
                 'Posthumous attributions', 'About', 'Criticism']
    # parse each section until reaching the External links section
    while not (node is None or (node.name == 'h2' and node.span.get_text() == "External links")):
        blacklisted = False
        for title in blacklist:
            if node.span.get_text().startswith(title):
                blacklisted = True
        if blacklisted:
            s = Section(node)
            node = s.end.next_sibling
        else:
            s = Section(node)
            s.propagate_source()
            quotes = quotes + s.collect_quotes()
            node = s.end.next_sibling
    return quotes


def parse_to_quotes(node):
    """Parse the beginning of a page until reaching the first quotes heading

    Args:
        node: first Beautiful Soup node in page.

    returns:
        Beautiful Soup node of first quotes heading.
    """
    found_quotes = False
    try:
        if node.name == 'h2':
            found_quotes = True
        while not found_quotes:
            node = node.next_sibling
            if node.name == 'h2':
                found_quotes = True
    except:
        return None
    return node


class Section:
    """ represents section of a wikiquotes page

    args:
        start_heading: node representing beginning of section
    """
    def __init__(self, start_heading):
        self.start = start_heading
        # node representing end of section
        self.end = None
        # is the title of this section a source name?
        self.is_source = False
        self.title = start_heading.span.get_text()
        # subsections of this section
        self.children = []
        # quotes in this section (not including subsections)
        self.quotes = []
        # heading level of this section
        self.level = int(self.start.name[1:])
        self.parse()
        self.determine_if_source()

    def parse(self):
        """Parse section, populating "children" and "quotes"
        """
        node = self.start
        while self.end is None:
            if node.next_sibling is None:
                self.end = node
            else:
                node = node.next_sibling
                if node.name == 'ul':
                    self.quotes.append(Quote(node))
                elif node.name in ['h' + str(i) for i in range(1, 6)]:
                    node_level = int(node.name[1:])
                    if node_level > self.level:
                        s = Section(node)
                        self.children.append(s)
                        node = s.end
                    else:
                        self.end = node.previous_sibling

    def determine_if_source(self):
        """Determine if the current section's title is a source
        """
        # titles ending in a parenthetical (usually with date) are generally
        # sources.
        p = re.compile(r'.*\(.*\)')
        m = p.match(self.title)
        if self.title in ['Quotes', 'Sourced']:
            self.is_source = False
            return
        # otherwise, sections that have no children, and where most quotes
        # don't appear to have a source, are usually sources
        if m and m.group() == self.title:
            self.is_source = True
            return
        quotes_lack_source = False
        n_quotes_with_source = sum(
            map(lambda x: x.potential_source is not None, self.quotes))
        n_quotes = len(self.quotes)
        if n_quotes > 0 and n_quotes_with_source / n_quotes < .5:
            quotes_lack_source = True
        has_children = len(self.children) > 0
        if quotes_lack_source and not has_children:
            self.is_source = True

    def propagate_source(self, higher_source=None):
        """set source attribute in the sections quotes, and apply to subsections
        """
        if higher_source:
            source = higher_source
        elif self.is_source:
            source = self.title
        else:
            source = None
        if source is None:
            for x in self.quotes:
                x.keep_potential_source()
            for x in self.children:
                x.propagate_source()
        else:
            for x in self.quotes:
                x.set_source(source)
            for x in self.children:
                x.propagate_source(source)

    def collect_quotes(self):
        """collect quotes from section and subsections

        returns:
           list of Quotes
        """
        quotes = [q for q in self.quotes if not q.invalid]
        childquotes = [q for s in self.children for q in s.collect_quotes()]
        return quotes + childquotes


class Quote:
    """ represents one quote in Wikiquote page

    args:
        text: node including quote
    """
    def __init__(self, text):
        self.text = text
        # source that the quote is drawn from
        self.source = None
        # potential source title found in quote
        self.potential_source = None
        self.quote = ''
        # is quote in foreign language?
        self.foreign = False
        # is quote in invalid format?
        self.invalid = False
        self.parse()

    def keep_potential_source(self):
        """set source to potential_source
        """
        self.source = self.potential_source

    def set_source(self, source_name):
        """set source to given source_name
        """
        self.source = source_name

    def parse(self):
        """parse quote node, setting quote and potential_source attributes
        """

        text = self.text.li

        # helper function to parse both BeautifulSoup tags and NavigableStrings
        def extract_text(x):
            if type(x).__name__ == "NavigableString":
                return x
            elif x.name == 'br':
                return '\n'
            else:
                return x.get_text()

        # helper function to get text from a bullet, ignoring potential
        # sub-bullets or images
        def get_bullet_parts(q):
            parts = []
            for c in q.children:
                if c.name == 'ul':
                    break
                elif c.name == 'div' and 'thumb' in c['class']:
                    pass
                elif c.name == 'a' and 'class' in c.attrs and 'autonumber' in c['class']:
                    pass
                else:
                    parts.append(c)
            return parts

        def is_english(quote, quote_parts=None):
            if not len(quote):
                return False
            alpha = 'abcdefghijklmnopqrstuvwzyz'
            spaceless = quote.replace(' ', '')
            prop_latin = sum(map(lambda x: x in alpha, spaceless.lower())) / len(spaceless)
            if prop_latin < .6:
                return False
            if len(quote) < 60:
                textlen = len(''.join([extract_text(x) for x in quote_parts]))
                try:
                    italiclen = len(''.join([extract_text(x) for x in quote_parts if x.name=='i']))
                except:
                    italiclen = 0
                if italiclen + 5 > textlen:
                    return False
                else:
                    return True
            else:
                if ('en' in [x.lang for x in langdetect.detect_langs(quote)]) or (langid.classify(quote)[0]=='en'):
                    return True
                else:
                    return False

        # get sub-bullets which might include source name
        meta_info = text.ul
        quote_parts = get_bullet_parts(text)
        try:
            quote = ''.join(map(extract_text, quote_parts)).strip()
            # quote in foreign language, try next subbullet
            if not is_english(quote, quote_parts):
                if meta_info:
                    bullets = meta_info.find_all('li')
                    quote_parts = get_bullet_parts(bullets[0])
                    quote = ''.join(map(extract_text, quote_parts)).strip()
                    # check if subbullet seems to be in english
                    if is_english(quote, quote_parts):
                        self.quote = ''.join(map(extract_text, quote_parts)).strip()
                        if len(bullets) > 1:
                            source_parts = get_bullet_parts(bullets[1])
                            self.potential_source = ''.join(map(extract_text, source_parts)).strip()
                    else:
                        self.invalid = True
                else:
                    self.invalid = True
                    print("foreign with no meta-info:", quote)
            else:
                self.quote = quote
                if meta_info:
                    source_parts = get_bullet_parts(meta_info.li)
                    self.potential_source = ''.join(map(extract_text, source_parts)).strip()
            # try to catch things like chapter headings that get through from bad parses
            badwords = ['p.', 'pp.', 'ch.', 'chapter', 'page', 'chap.']
            if len(quote) < 25 and sum([(b in quote.lower().split()) for b in badwords]) > 0:
                self.invalid = True
            if ('\\displaystyle' in quote):
                self.invalid = True
            badwords = ['p.', 'ch.', 'chapter', 'page', 'chap.', 'act']
            if self.potential_source and sum([self.potential_source.lower().startswith(b) for b in badwords]) > 0:
                self.potential_source = None
        except Exception as e:
            print(e)
            print(quote_parts, meta_info)
            self.invalid = True
