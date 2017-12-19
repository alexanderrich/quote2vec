from db import Quote, Source, Person, Keyword, Session
from sqlalchemy_fulltext import FullTextSearch
import sqlalchemy_fulltext.modes as FullTextMode
from sqlalchemy.sql.expression import func
from gensim.models import Doc2Vec
from gensim.similarities import Similarity
import numpy as np
from sklearn.decomposition import PCA


class ModelInterface:

    def __init__(self, model_filename, index_filename):
        # self.dv = KeyedVectors.load(docvec_filename)
        self.model = Doc2Vec.load(model_filename)
        self.index = Similarity.load(index_filename)

    def get_random(self, randtype):
        session = Session()
        types = {'person': Person, 'source': Source, 'quote': Quote}
        id = (session.query(types[randtype])
              .order_by(func.random())
              .limit(1)
              .one().id)
        return id

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
        sims = self.index[self.model.docvecs[id]]
        sims = sorted(enumerate(sims), key=lambda item: -item[1])
        sims = sims[:n]
        ids = [i[0]+1 for i in sims]
        # make sure actual quote is present as most similar item
        ids = [i for i in ids if i != id]
        ids = [id] + ids
        ids = ids[:n]
        # retrieve actual quotes
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

    def get_keyword_quotes(self, keywords, n=25):
        v = self.model.infer_vector(keywords, steps=300)
        sims = self.index[v]
        sims = sorted(enumerate(sims), key=lambda item: -item[1])
        sims = sims[:n]
        ids = [i[0]+1 for i in sims]
        # retrieve actual quotes
        quotebytes = np.array(ids).tostring()
        keyword = Keyword(quotes=quotebytes)
        session = Session()
        session.add(keyword)
        session.commit()
        keyword_id = keyword.id
        quotes = session.query(Quote).filter(Quote.id.in_(ids)).all()
        quotes_dict = {q.id: q for q in quotes}
        quotes = [quotes_dict[i] for i in ids]
        source_ids = set([q.source_id for q in quotes if q.source_id is not None])
        sources = session.query(Source).filter(Source.id.in_(source_ids)).all()
        person_ids = set([q.person_id for q in quotes])
        people = session.query(Person).filter(Person.id.in_(person_ids)).all()
        session.close()
        return quotes, sources, people, keyword_id

    def get_keyword_quotes_cached(self, id):
        session = Session()
        keyword = session.query(Keyword).filter(Keyword.id == id).one()
        ids = np.fromstring(keyword.quotes, dtype=np.int64)
        ids = [int(id) for id in ids]
        quotes = session.query(Quote).filter(Quote.id.in_(ids)).all()
        quotes_dict = {q.id: q for q in quotes}
        quotes = [quotes_dict[i] for i in ids]
        source_ids = set([q.source_id for q in quotes if q.source_id is not None])
        sources = session.query(Source).filter(Source.id.in_(source_ids)).all()
        person_ids = set([q.person_id for q in quotes])
        people = session.query(Person).filter(Person.id.in_(person_ids)).all()
        session.close()
        return quotes, sources, people

    def get_docvec(self, id):
        return self.model.docvecs[id]

    def get_vis_coords(self, ids):
        # vecs = np.array([self.get_docvec(i) for i in ids])
        vecs = [self.get_docvec(i) for i in ids]
        vecs = np.array([v / np.linalg.norm(v) for v in vecs])
        if len(ids) == 1:
            return np.array([[0, 0]])
        else:
            return PCA(n_components=2).fit_transform(vecs)
