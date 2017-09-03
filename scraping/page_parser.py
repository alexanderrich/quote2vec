from bs4 import BeautifulSoup
import re


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
                 'Quotations regarding', 'See also', 'References',
                 'Posthumous attributions', 'About', 'Criticism']
    # parse each section until reachign the External links section
    while not (node.name == 'h2' and node.span.get_text() == "External links"):
        blacklisted = False
        for title in blacklist:
            if node.span.get_text().startswith(title):
                blacklisted = True
        if blacklisted:
            s = Section(node)
            node = s.end.next_sibling
        else:
            s = Section(node)
            s.propagate_work()
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
        # is the title of this section a Work name?
        self.is_work = False
        self.title = start_heading.span.get_text()
        # subsections of this section
        self.children = []
        # quotes in this section (not including subsections)
        self.quotes = []
        # heading level of this section
        self.level = int(self.start.name[1:])
        self.parse()
        self.determine_if_work()

    def parse(self):
        """Parse section, populating "children" and "quotes"
        """
        node = self.start
        while self.end is None:
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

    def determine_if_work(self):
        """Determine if the current section's title is a Work
        """
        # titles ending in a parenthetical (usually with date) are generally
        # works.
        p = re.compile(r'.*\(\w*\)')
        m = p.match(self.title)
        if self.title in ['Quotes', 'Sourced']:
            self.is_work = False
            return
        # otherwise, sections that have no children, and where most quotes
        # don't appear to have a Work, are usually Works
        if m and m.group() == self.title:
            self.is_work = True
            return
        quotes_lack_work = False
        n_quotes_with_work = sum(
            map(lambda x: x.potential_work is not None, self.quotes))
        n_quotes = len(self.quotes)
        if n_quotes > 0 and n_quotes_with_work / n_quotes < .5:
            quotes_lack_work = True
        has_children = len(self.children) > 0
        if quotes_lack_work and not has_children:
            self.is_work = True

    def propagate_work(self, higher_work=None):
        """set work attribute in the sections quotes, and apply to subsections
        """
        if higher_work:
            work = higher_work
        elif self.is_work:
            work = self.title
        else:
            work = None
        if work is None:
            for x in self.quotes:
                x.keep_potential_work()
            for x in self.children:
                x.propagate_work()
        else:
            for x in self.quotes:
                x.set_work(work)
            for x in self.children:
                x.propagate_work(work)

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
        # work that the quote is drawn from
        self.work = None
        # potential work title found in quote
        self.potential_work = None
        self.quote = ''
        # is quote in foreign language?
        self.foreign = False
        # is quote in invalid format?
        self.invalid = False
        self.parse()

    def keep_potential_work(self):
        """set work to potential_work
        """
        self.work = self.potential_work

    def set_work(self, work_name):
        """set work to given work_name
        """
        self.work = work_name

    def parse(self):
        """parse quote node, setting quote and potential_work attributes
        """

        text = self.text.li

        # helper function to parse both BeautifulSoup tags and NavigableStrings
        def extract_text(x):
            if type(x).__name__ == "NavigableString":
                return x
            else:
                return x.get_text()

        # helper function to get text from a bullet, ignoring potential
        # sub-bullets or images
        def get_bullet_parts(q):
            parts = []
            for c in q.children:
                if c.name == 'ul':
                    break
                elif not (c.name == 'div' and 'thumb' in c['class']):
                    parts.append(c)
            return parts

        # get sub-bullets which might include work name
        meta_info = text.ul
        quote_parts = get_bullet_parts(text)
        try:
            # quote is in foreign language with translation
            if len(quote_parts) == 1 and quote_parts[0].name == 'i' and meta_info:
                bullets = meta_info.find_all('li')
                quote_parts = get_bullet_parts(bullets[0])
                self.quote = ''.join(map(extract_text, quote_parts)).strip()
                if len(bullets) > 1:
                    work_parts = get_bullet_parts(bullets[1])
                    self.potential_work = ''.join(map(extract_text, work_parts)).strip()
            else:
                self.quote = ''.join(map(extract_text, quote_parts)).strip()
                if meta_info:
                    work_parts = get_bullet_parts(meta_info.li)
                    self.potential_work = ''.join(map(extract_text, work_parts)).strip()
        except Exception as e:
            print(e)
            print(quote_parts, meta_info)
            self.invalid = True
