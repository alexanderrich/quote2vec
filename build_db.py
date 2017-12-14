from sqlalchemy import text
from db import engine, Base, Person, Source, Quote, Session
from page_retriever import get_person_page, get_all_people_pages
from page_parser import parse_html
from time import sleep

sql = text('DROP TABLE IF EXISTS quotes;')
result = engine.execute(sql)
sql = text('DROP TABLE IF EXISTS sources;')
result = engine.execute(sql)
sql = text('DROP TABLE IF EXISTS people;')
result = engine.execute(sql)

Base.metadata.create_all(engine)


def add_data(name):
    try:
        html = open("raw/"+name+".txt", 'r').read()
        print("loaded", name, 'from disk')
    except:
        # print("retreiving", name)
        # html = get_person_page(name)
        # if not html:
        #     return None
        # with open("raw/" + name + ".txt", 'w') as f:
        #     f.write(html)
        # sleep(2.5)
        return None

    try:
        quotes = parse_html(html)
    except:
        print("exception parsing", name)
        quotes = None

    sources = {}
    if quotes:
        for q in quotes:
            if q.source is None:
                q.source = "*None*"
            if q.source in sources:
                sources[q.source].append(q.quote)
            else:
                sources[q.source] = [q.quote]

        session = Session()
        person = Person(name=name)
        for s in sources:
            if s is not '*None*':
                source = Source(source=s)
                person.sources.append(source)
            for q in sources[s]:
                quote = Quote(quote=q)
                person.quotes.append(quote)
                if s is not '*None*':
                    source.quotes.append(quote)
        session.add(person)
        session.commit()
        session.close()


try:
    with open('raw/_people_list_.txt', 'r') as f:
        people_pages = f.readlines()
    people_pages = [p.strip() for p in people_pages ]
    people_pages = [p for p in people_pages if p not in
                    ['Anonymous', 'Rani Mukerji', 'Sappho', 'George Herbert',
                     'Noel Fielding', 'Giovanni Rucellai', 'Pope Sixtus V', 'Geoffrey Chaucer', 'Stefano Guazzo']]
    print("loaded people list from disk")
except:
    people_pages = get_all_people_pages()
    # Get rid of a few weirdly formatted pages
    people_pages = [p for p in people_pages if p not in
                    ['Anonymous', 'Rani Mukerji', 'Sappho', 'George Herbert',
                     'Noel Fielding', 'Giovanni Rucellai', 'Pope Sixtus V', 'Geoffrey Chaucer', 'Stefano Guazzo']] #, 'Poet Pearl', 'Antonio Porchia'
    people_pages = set(people_pages)
    with open('raw/_people_list_.txt', 'w') as f:
        f.writelines(['{}\n'.format(item) for item in people_pages])

for p in people_pages:
    add_data(p)
