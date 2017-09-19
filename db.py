from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

engine = create_engine('mysql+mysqlconnector://alex:asr5991@localhost/wikiquote')

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


Session = sessionmaker(bind=engine)
