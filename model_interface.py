from db import Quote, Source, Person, Session
from sqlalchemy_fulltext import FullTextSearch
import sqlalchemy_fulltext.modes as FullTextMode
from sqlalchemy.sql.expression import func
from gensim.models import KeyedVectors
from gensim.similarities import Similarity
import numpy as np
from sklearn.decomposition import PCA


class ModelInterface:

    def __init__(self, docvec_filename, index_filename):
        self.dv = KeyedVectors.load(docvec_filename)
        self.index = Similarity.load(index_filename)

    # def get_quotes_byid(self, id, id_type='quote'):
    #     session = Session()
    #     if id_type=='quote':
    #         quote = (session.query(Quote)
    #                  .filter(Quote.id == id)
    #                  .one())
    #         person = (session.query(Person)
    #                   .filter(Person.id == quote.person_id)
    #                   .one())
    #         source = (session.query(Source)
    #                   .filter(Person.id == quote.person_id)
    #                   .one_or_none())
    #     if id_type == 'person':
    #         person = (session.query(Person)
    #                   .filter(Person.id == id)
    #                   .one())
    #         quote =

    def get_person_suggestions(self, query, n=10):
        session = Session()
        query_ft = query
        for char in '()+-*~@<>"':
            query_ft = query_ft.replace(char, ' ')
        people = (session.query(Person)
                  .filter(FullTextSearch(query_ft + '*', Person, FullTextMode.BOOLEAN))
                  .filter(Person.name.like('%'+query.strip()+'%'))
                  .order_by(func.length(Person.name))
                  .limit(n)
                  .all())
        session.close()
        return people

    def get_source_suggestions(self, query, n=10):
        session = Session()
        query_ft = query
        for char in '()+-*~@<>"':
            query_ft = query_ft.replace(char, ' ')
        sources = (session.query(Source)
                   .filter(FullTextSearch(query_ft + '*', Source, FullTextMode.BOOLEAN))
                   .filter(Source.source.like('%'+query.strip()+'%'))
                   .order_by(func.length(Source.source))
                   .limit(n)
                   .all())
        session.close()
        return sources

    def get_quote_suggestions(self, query, n=10):
        session = Session()
        query_ft = query
        for char in '()+-*~@<>"':
            query_ft = query.replace(char, ' ')
        quotes = (session.query(Quote)
                  .filter(FullTextSearch(query_ft + '*', Quote, FullTextMode.BOOLEAN))
                  .filter(Quote.quote.like('%'+query.strip()+'%'))
                  .order_by(func.length(Quote.quote))
                  .limit(n)
                  .all())
        session.close()
        return quotes

    def get_quote(self, id):
        session = Session()
        quote = (session.query(Quote)
                 .filter(Quote.id == id)
                 .one())
        person = (session.query(Person)
                  .filter(Person.id == quote.person_id)
                  .one())
        if quote.source_id:
            source = (session.query(Source)
                      .filter(Source.id == quote.source_id)
                      .one())
            return [quote], [source], [person]
        session.close()
        return [quote], [], [person]

    def get_source_quotes(self, id):
        session = Session()
        quotes = (session.query(Quote)
                  .filter(Quote.source_id == id)
                  .all())
        source = (session.query(Source)
                  .filter(Source.id == id)
                  .one())
        person = (session.query(Person)
                  .filter(Person.id == source.person_id)
                  .one())
        session.close()
        return quotes, [source], [person]

    def get_person_quotes(self, id):
        session = Session()
        quotes = (session.query(Quote)
                  .filter(Quote.person_id == id)
                  .all())
        source = (session.query(Source)
                  .filter(Source.person_id == id)
                  .all())
        person = (session.query(Person)
                  .filter(Person.id == id)
                  .one())
        session.close()
        return quotes, source, [person]

    def get_similar_quotes(self, id, n=25):
        sims = self.index[self.dv[id]]
        sims = sorted(enumerate(sims), key=lambda item: -item[1])
        sims = sims[:n]
        ids = [i[0]+1 for i in sims]
        session = Session()
        quotes = session.query(Quote).filter(Quote.id.in_(ids)).all()
        quotes_dict = {q.id: q for q in quotes}
        quotes = [quotes_dict[i] for i in ids]
        source_ids = set([q.source_id for q in quotes if q.source_id is not None])
        sources = session.query(Source).filter(Source.id.in_(source_ids)).all()
        person_ids = set([q.person_id for q in quotes])
        people = session.query(Person).filter(Person.id.in_(person_ids)).all()
        session.close()
        return quotes, sources, people

    # def get_quotes(self, person_name, source_name=None):
    #     session = Session()
    #     person = (session.query(Person)
    #               .filter(Person.name == person_name)
    #               .one_or_none())
    #     if not person:
    #         session.close()
    #         return None
    #     if source_name is None:
    #         quote_list = (session.query(Quote)
    #                       .filter(Quote.person_id == person.id)
    #                       .all())
    #     else:
    #         source = (session.query(Source)
    #                   .filter(and_(Source.source == source_name,
    #                                Source.person_id == person.id))
    #                   .one_or_none())
    #         if not source:
    #             session.close()
    #             return None
    #         quote_list = (session.query(Quote)
    #                       .filter(Quote.source_id == source.id)
    #                       .all())
    #     session.close()
    #     return quote_list

    def get_docvec(self, id):
        return self.dv[id]

    def get_vis_coords(self, ids):
        # vecs = np.array([self.get_docvec(i) for i in ids])
        vecs = [self.get_docvec(i) for i in ids]
        vecs = np.array([v / np.linalg.norm(v) for v in vecs])
        if len(ids) == 1:
            return np.array([[0, 0]])
        else:
            return PCA(n_components=2).fit_transform(vecs)
