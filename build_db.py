from sqlalchemy import create_engine
from sqlalchemy import Table, Column, Integer, String, ForeignKey, text
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from page_retriever import get_person_page, get_all_people_pages
from page_parser import parse_html
from time import sleep

engine = create_engine('mysql+mysqlconnector://alex:asr5991@localhost/wikiquote')

sql = text('DROP TABLE IF EXISTS quotes;')
result = engine.execute(sql)
sql = text('DROP TABLE IF EXISTS sources;')
result = engine.execute(sql)
sql = text('DROP TABLE IF EXISTS people;')
result = engine.execute(sql)

Base = declarative_base()

class Person(Base):
    __tablename__ = 'people'
    id = Column(Integer, primary_key=True)
    name = Column(String(300))

    sources = relationship("Source", back_populates='person',
                          cascade="all, delete, delete-orphan")
    quotes = relationship("Quote", back_populates='person',
                         cascade="all, delete, delete-orphan")

    def __repr__(self):
        return "<Person(name='{}')>".format(self.name)


class Source(Base):
    __tablename__ = 'sources'
    id = Column(Integer, primary_key=True)
    source = Column(String(5000))
    person_id = Column(Integer, ForeignKey('people.id'))

    person = relationship("Person", back_populates='sources')
    quotes = relationship("Quote", back_populates='source')

    def __repr__(self):
        if len(self.source)>50:
            return "<Source(source='{}')".format(self.source[:50])
        else:
            return "<Source(source='{}')".format(self.source)


class Quote(Base):
    __tablename__ = 'quotes'
    id = Column(Integer, primary_key=True)
    quote = Column(String(20000))
    person_id = Column(Integer, ForeignKey('people.id'))
    source_id = Column(Integer, ForeignKey('sources.id'), nullable=True)

    person = relationship("Person", back_populates='quotes')
    source = relationship("Source", back_populates='quotes')

    def __repr__(self):
        if len(self.quote) > 50:
            return"<Quote(quote='{}')".format(self.quote[:50])
        else:
            return"<Quote(quote='{}')".format(self.quote)


Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)


def add_data(name):
    try:
        html = open("raw/"+name+".txt", 'r').read()
        print("loaded", name, 'from disk')
    except:
        print("retreiving", name)
        html = get_person_page(name)
        if not html:
            return None
        with open("raw/" + name + ".txt", 'w') as f:
            f.write(html)
        sleep(2.5)

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


people_pages = get_all_people_pages()
people_pages = [p for p in people_pages if p not in ['Anonymous']]
people_pages = set(people_pages)

for p in people_pages:
    add_data(p)
