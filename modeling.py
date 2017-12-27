from db import Quote, Session
from gensim import corpora, models, similarities
from random import shuffle
import numpy as np
import spacy
nlp = spacy.load('en')


def build_corpus(filename=None):
    """
    process all quotes in the database and return a list of tokenized training data.
    Optionally, save the processed data to a plain text file as well for later use.
    """
    session = Session()
    original = session.query(Quote).all()
    session.close()
    quotes = [q.quote for q in original]

    def lemma(t):
        if t.lemma_ == "-PRON-":
            return str(t).lower()
        if t.lemma_ == 'i.':
            return 'i'
        return t.lemma_

    def spacify(quote):
        quote = quote.replace("’", "'").replace("—", " ").replace("-", " ").replace("|", " ")
        replacespace = '\\`*_{}[]()<>@^#+~-!?:;|'
        for ch in replacespace:
            quote = quote.replace(ch, ' ')
        spacy_quote = nlp(quote)
        return spacy_quote

    parsed = [[lemma(q) for q in spacify(quote) if q.pos_ not in ['PUNCT', 'SPACE']] for quote in quotes]
    quoteid = [q.id for q in original]
    sourceid = [q.source_id for q in original]
    sourceid = [s if s is not None else -1 for s in sourceid]
    personid = [q.person_id for q in original]
    if filename:
        parsedstrings = [" ".join(q) + "\n" for q in parsed]
        parsedstrings = ["{}|{}|{}|{}".format(str(quoteid[i]),
                                              str(sourceid[i]),
                                              str(personid[i]),
                                              parsedstrings[i])
                         for i in range(len(parsedstrings))]
        with open(filename, 'w') as f:
            f.writelines(parsedstrings)
    return list(zip(quoteid, sourceid, personid, parsed))


def load_corpus(filename):
    """
    load list of tokenized training data from plain text format produced by build_corpus
    """
    with open(filename, 'r') as f:
        parsed = f.readlines()
        parsed = [q.strip().split("|") for q in parsed]
        parsed = [(int(q[0]), int(q[1]), int(q[2]), q[3].strip().split()) for q in parsed]
    return parsed


class BaseModel:
    """
    Basic class for training models on quote data. Contains score function for evaluating models
    across any gensim model type that can create a similarity index.
    """

    def __init__(self, parsed, name):
        self.modelfn = None
        self.model = None
        self.transformed = None
        self.index = None
        self.dictionary = None
        self.id2idx = {v[0]: i for i, v in enumerate(parsed)}
        self.id2source = {v[0]: v[1] for v in parsed}
        self.id2person = {v[0]: v[2] for v in parsed}
        self.parsed = parsed

    def get_similar(self, id, n=10):
        sims = self.index[self.transformed[id]]
        sims = sorted(enumerate(sims), key=lambda item: -item[1])
        sims = sims[:n]
        session = Session()
        ids = [i[0] for i in sims]
        quotes = session.query(Quote).filter(Quote.id.in_(ids)).all()
        session.close()
        return sims, quotes

    def score(self, n_samples=100):
        """
        This function evaluates the proportion of quotes for which a quote chosen
        from the same {person, source} is more similar than a randomly chosen
        quote. The function estimates this proportion using n_samples samples,
        and calculates the value for both person pairs and source paris,
        returning both values and the average of the two.
        """
        # choose random set of quotes to test
        sample = [x for x in range(len(self.parsed))]
        shuffle(sample)
        sample = sample[:n_samples]
        sample = [self.parsed[s][0] for s in sample]
        # build lookup tables to go from chosen quote to all other quotes from
        # that person or source
        person2quotes = {}
        for qid, pid in self.id2person.items():
            if pid not in person2quotes:
                person2quotes[pid] = [qid]
            else:
                person2quotes[pid].append(qid)
        quote2personquotes = {}
        for p, qlist in person2quotes.items():
            for q in qlist:
                quote2personquotes[q] = qlist
        source2quotes = {}
        for qid, sid in self.id2source.items():
            if sid > -1:
                if sid not in source2quotes:
                    source2quotes[sid] = [qid]
                else:
                    source2quotes[sid].append(qid)
        quote2sourcequotes = {}
        for p, qlist in source2quotes.items():
            for q in qlist:
                quote2sourcequotes[q] = qlist
        # for each target quote, choose a random quote and a quote from the
        # same {source, person}, and see if the source or person quote is more
        # similar than the random quote.
        personacc = []
        sourceacc = []
        for i in sample:
            sims = self.index.similarity_by_id(self.id2idx[i])
            ids = quote2personquotes[i]
            idxs = [self.id2idx[id] for id in ids if id != i]
            if len(idxs):
                sample_control = np.random.choice(sims)
                sample_person = np.random.choice(np.array(sims)[idxs])
                personacc.append(sample_person > sample_control)
            if i in quote2sourcequotes:
                ids = quote2sourcequotes[i]
                idxs = [self.id2idx[id] for id in ids if id != i]
                if len(idxs):
                    sample_control = np.random.choice(sims)
                    sample_source = np.random.choice(np.array(sims)[idxs])
                    sourceacc.append(sample_source > sample_control)
        personacc = np.mean(personacc)
        sourceacc = np.mean(sourceacc)
        acc = (sourceacc + personacc) / 2
        return (personacc, sourceacc, acc)


class LsiWrapper(BaseModel):
    """Wrapper for model using Latent Semantic Indexing"""
    def __init__(self, parsed, name, num_topics):
        super().__init__(parsed, name)
        dictionary = corpora.Dictionary(parsed)
        bow = [dictionary.doc2bow(q) for q in parsed]
        tfidf = models.TfidfModel(bow)
        try:
            lsi = models.LsiModel.load('models/'+name+'.model')
        except:
            lsi = models.LsiModel(tfidf[bow], id2word=dictionary, num_topics=num_topics)
            lsi.save('models/'+name+'.model')
        self.dictionary = dictionary
        self.transformed = lsi[tfidf[bow]]
        self.modelfn = lambda q: lsi[tfidf[dictionary.doc2bow(q)]]
        self.model = lsi
        try:
            self.index = similarities.Similarity.load('similarities/'+name+'.index')
        except:
            self.index = similarities.Similarity('similarities/'+name, self.transformed, num_topics)
            self.index.save('similarities/'+name+'.index')


class Doc2VecWrapper(BaseModel):
    """Wrapper for model using Doc2Vec"""
    def __init__(self, parsed, name, **kwargs):
        super().__init__(parsed, name)
        self.name = name
        self.taggeddocs = [models.doc2vec.TaggedDocument(x[3], [x[0]]) for x in parsed]
        try:
            self.model = models.doc2vec.Doc2Vec.load('models/'+name+'.model')
            self.index = similarities.Similarity.load('similarities/'+name+'.index')
            self.transformed = self.model.docvecs
        except:
            self.model = models.doc2vec.Doc2Vec(**kwargs)
            self.model.build_vocab(self.taggeddocs)

    def train(self, alpha):
        shuffle(self.taggeddocs)
        self.model.alpha = alpha
        self.model.min_alpha = alpha
        self.model.train(self.taggeddocs, total_examples=self.model.corpus_count, epochs=1)
        print("finished epoch")

    def finish_training(self, percentile):
        self.model.save('models/'+self.name+'.model')
        self.transformed = self.model.docvecs[[x[0] for x in self.parsed]]

        # normalize vectors for cosine similarity calculation, but penalize
        # vectors under a certain length percentile
        norms = []
        for v in self.transformed:
            norms.append(np.linalg.norm(v))
        cutoff = np.percentile(norms, percentile)
        print(cutoff)
        normalized = [v / np.max([np.power(np.linalg.norm(v)/cutoff, .5),
                                  np.linalg.norm(v)/cutoff])
                      for v in self.transformed]
        self.index = similarities.Similarity('similarities/'+self.name,
                                             normalized, self.transformed.shape[1])
        self.index.save('similarities/'+self.name+'.index')

    def get_docvec(self, id):
        return self.model.docvecs[id]


if __name__=="__main__":
    parsed = build_corpus('tokenized.txt')
    model = Doc2VecWrapper(parsed, 'dbow300', size=300,
                           min_count=5, dm=0, negative=15,
                           dbow_words=1, workers=8, sample=10**-5)

    # optionally, pre-populate with google news word vectors
    # model.model.intersect_word2vec_format('GoogleNews-vectors-negative300.bin', binary=True, lockf=1.0)

    for i in range(32):
        model.train(.025*(.95**i))
    model.finish_training(60)
    print(model.score(n_samples=10000))
