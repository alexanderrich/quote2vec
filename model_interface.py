from db import Quote, Source, Person, Session
from sqlalchemy import and_
from gensim.models import KeyedVectors
from gensim.similarities import Similarity


class ModelInterface:

    def __init__(self, docvec_filename, index_filename):
        self.dv = KeyedVectors.load(docvec_filename)
        self.index = Similarity.load(index_filename)

    def get_quotes(self, person_name, source_name=None):
        session = Session()
        person = (session.query(Person)
         .filter(Person.name == person_name)
         .one_or_none())
        if not person:
            return None
        if source_name is None:
            quote_list = (session.query(Quote)
                          .filter(Quote.person_id==person.id)
                          .all())
        else:
            source = (session.query(Source)
                      .filter(and_(Source.source==source_name,
                                   Source.person_id==person.id))
                      .one_or_none())
            if not source:
                return None
            quote_list = (session.query(Quote)
                          .filter(Quote.source_id==source.id)
                          .all())
        return quote_list

    def get_similar(self, id, n=10):
        sims = self.index[self.dv[id]]
        sims = sorted(enumerate(sims), key=lambda item: -item[1])
        sims = sims[:n]
        session = Session()
        ids = [i[0] for i in sims]
        quotes = session.query(Quote).filter(Quote.id.in_(ids)).all()
        session.close()
        return quotes, sims


    def get_docvec(self, id):
        return self.dv[id]
