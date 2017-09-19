import requests
import json
import time
from bs4 import BeautifulSoup

from page_parser import parse_html


def get_person_page(title):
    payload = {'action': 'parse',
               'format': 'json',
               'prop': 'text',
               'page': title}
    r = requests.get('http://en.wikiquote.org/w/api.php', payload,
                     headers={"user-agent": "python-requests (machine-learning" +
                              " project on wikiquote corpus, email:" +
                              " alexandersrich at gmail dot com)"})
    try:
        html = json.loads(r.text)['parse']['text']['*']
    except:
        html = None
    return html

def parse_people_page(html):
    soup = BeautifulSoup(html, 'html.parser')
    soup = soup.contents[0]
    names = []
    for s in soup.contents:
        if s.name == 'ul':
            names = names + parse_ul(s)
    return names


def parse_ul(node):
    items = node.find_all('li')
    names = []
    for i in items:
        try:
            names.append(i.a['title'])
        except:
            print('invalid bullet')
    return names


def get_people_page(title):
    payload = {'action': 'parse',
               'format': 'json',
               'prop': 'text',
               'page': title}
    r = requests.get('http://en.wikiquote.org/w/api.php', payload,
                     headers={"user-agent": "python-requests (machine-learning" +
                              " project on wikiquote corpus, email:" +
                              " alexandersrich at gmail dot com)"})
    try:
        html = json.loads(r.text)['parse']['text']['*']
    except:
        return None
    return parse_people_page(html)


def get_all_people_pages():
    page_names = ['List of people by name, A',
                  'List of people by name, B',
                  'List of people by name, C',
                  'List of people by name, D',
                  'List of people by name, E–F',
                  'List of people by name, G',
                  'List of people by name, H',
                  'List of people by name, I–J',
                  'List of people by name, K',
                  'List of people by name, L',
                  'List of people by name, M',
                  'List of people by name, N–O',
                  'List of people by name, P',
                  'List of people by name, Q–R',
                  'List of people by name, S',
                  'List of people by name, T–V',
                  'List of people by name, W–Z']
    names = []
    for page in page_names:
        print(page)
        names = names + get_people_page(page)
        time.sleep(2.5)
    return names
