from db import Quote, Source, Person, Keyword, QuoteVec, Session
from sqlalchemy_fulltext import FullTextSearch
import sqlalchemy_fulltext.modes as FullTextMode
from sqlalchemy.sql.expression import func
from gensim.models import Doc2Vec
from gensim.similarities import Similarity
import numpy as np
from sklearn.decomposition import PCA
import nltk


class ModelInterface:

    def __init__(self, model_filename, index_filename):
        # lemmatizer and model for keyword inference
        self.lemmatize = nltk.stem.WordNetLemmatizer().lemmatize
        self.model = Doc2Vec.load(model_filename)
        # index for similarity queries
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
        # replace problematic characters for fulltext search
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
        # replace problematic characters for fulltext search
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
        # replace problematic characters for fulltext search
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

    # get group of quotes similar to a given quote
    def get_similar_quotes(self, id, n=25):
        sims = self.index[self.get_docvecs([id])[0]]
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

    # get group of quotes similar to keyword string
    def get_keyword_quotes(self, keywords, n=25):

        # function to convert incompatible nltk POS tags
        def get_pos(treebank_tag):
            if treebank_tag.startswith('J'):
                return 'a'
            elif treebank_tag.startswith('V'):
                return 'v'
            elif treebank_tag.startswith('N'):
                return 'n'
            elif treebank_tag.startswith('R'):
                return 'r'
            else:
                return ''

        keywords = nltk.tokenize.word_tokenize(keywords)
        keywords = nltk.pos_tag(keywords)
        keywords = [self.lemmatize(w[0], get_pos(w[1])) if get_pos(w[1]) != '' else w[0] for w in keywords]
        keywords = [k for k in keywords if k in self.model.wv.vocab]

        # if no words in the vocab, just return garbage...
        if len(keywords) == 0:
            keywords = ['']
        # duplicate short keyword strings to get in enough training
        base_keywords = keywords
        while len(keywords) < 20:
            keywords = keywords + base_keywords

        # create new docvec using model
        v = self.model.infer_vector(keywords, steps=300)
        sims = self.index[v]
        sims = sorted(enumerate(sims), key=lambda item: -item[1])
        sims = sims[:n]
        ids = [i[0]+1 for i in sims]

        # cache keyword's similar quotes in the db. This means when this
        # keyword is needed in the future (e.g., to update PCA coords), vector
        # and similarity isn't recomputed
        quotebytes = np.array(ids).tostring()
        keyword = Keyword(quotes=quotebytes)
        session = Session()
        session.add(keyword)
        session.commit()
        keyword_id = keyword.id

        # retrieve actual quotes
        quotes = session.query(Quote).filter(Quote.id.in_(ids)).all()
        quotes_dict = {q.id: q for q in quotes}
        quotes = [quotes_dict[i] for i in ids]
        source_ids = set([q.source_id for q in quotes if q.source_id is not None])
        sources = session.query(Source).filter(Source.id.in_(source_ids)).all()
        person_ids = set([q.person_id for q in quotes])
        people = session.query(Person).filter(Person.id.in_(person_ids)).all()
        session.close()
        return quotes, sources, people, keyword_id

    # get quotes similar to keyword, for keyword string that's already been
    # computed and cached
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

    # get docvecs for list of quote ids
    def get_docvecs(self, ids):
        session = Session()
        docvecs = (session
                   .query(QuoteVec)
                   .filter(QuoteVec.id.in_(ids))
                   .all())
        # sort ids back into given order
        order = np.argsort(ids)
        docvecs_empty = [None] * len(docvecs)
        for i in range(len(docvecs)):
            docvecs_empty[order[i]] = docvecs[i]

        # get docvecs from byte strings
        docvecs = [np.fromstring(d.vec, np.float32) for d in docvecs_empty]
        return docvecs

    # get PCA coordinates for list of quote ids
    def get_vis_coords(self, ids):
        vecs = self.get_docvecs(ids)
        vecs = np.array([v / np.linalg.norm(v) for v in vecs])
        if len(ids) == 1:
            return np.array([[0, 0]])
        else:
            return PCA(n_components=2).fit_transform(vecs)


# utility to load all docvecs from a model into the database and then resave
# the model with docvecs deleted
def build_docvec_table(model_filename):
    model = Doc2Vec.load(model_filename + '.model')
    docvecs = model.docvecs
    session = Session()
    for i in range(len(docvecs)):
        qv = QuoteVec(id=i, vec=docvecs[i].tostring())
        session.add(qv)
        session.commit()
    session.close()
    model.docvecs = []
    model.save(model_filename + '_deletetraining.model')
