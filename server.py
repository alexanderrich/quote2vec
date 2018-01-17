from flask import Flask, request, render_template, jsonify
from model_interface import ModelInterface
from sqlalchemy.orm.exc import NoResultFound
import re


app = Flask(__name__)

mi = ModelInterface('models/dbow300_min5neg15adjustcutoff60_deletetraining.model',
                    'similarities/dbow300_min5neg15adjustcutoff60.index')

@app.route('/')
@app.route('/index')
def index():
    return render_template('quote2vec.html')

# get random group
@app.route('/random/<randtype>')
def get_random(randtype):
    return jsonify({'id': mi.get_random(randtype)})


# get group with given id
@app.route('/group/<groupid>')
def get_quote_group(groupid):
    match = re.match(r"([a-z]+)([0-9]+)", groupid, re.I)
    grouptype = match.group(1)
    id = int(match.group(2))
    try:
        if grouptype == 'quote':
            quotes, sources, people = mi.get_similar_quotes(id)
        elif grouptype == 'source':
            quotes, sources, people = mi.get_source_quotes(id)
        elif grouptype == 'person':
            quotes, sources, people = mi.get_person_quotes(id)
        elif grouptype == 'keyword':
            quotes, sources, people = mi.get_keyword_quotes_cached(id)
        quotes = [{'quote': q.quote,
                   'id': q.id,
                   'source_id': q.source_id,
                   'person_id': q.person_id} for q in quotes]
        people = [{'name': p.name,
                   'id': p.id} for p in people]
        sources = [{'source': s.source,
                    'id': s.id,
                    'person_id': s.person_id} for s in sources]
        response = {'quotes': quotes, 'people': people, 'sources': sources}
    except NoResultFound:
        response = {'error': "No result found."}
    return jsonify(response)

# get quotes for novel keyword string. Uses POST request to get keyword
# string.
@app.route('/keywords', methods=['POST'])
def get_keyword_quotes():
    keywords = request.get_json()['keywords']
    quotes, sources, people, keyword_id = mi.get_keyword_quotes(keywords)
    quotes = [{'quote': q.quote,
               'id': q.id,
               'source_id': q.source_id,
               'person_id': q.person_id} for q in quotes]
    people = [{'name': p.name,
               'id': p.id} for p in people]
    sources = [{'source': s.source,
                'id': s.id,
                'person_id': s.person_id} for s in sources]
    response = {'keyword_id': keyword_id,
                'quotes': quotes,
                'people': people,
                'sources': sources}
    return jsonify(response)

# Get pca coords for list of quote groups.
@app.route('/coords/<groupstring>')
def get_group_coords(groupstring):
    groupstrings = groupstring.split('&')
    groups = []
    for g in groupstrings:
        match = re.match(r"([a-z]+)([0-9]+)", g, re.I)
        groups.append((match.group(1), int(match.group(2))))
    grouplists = []
    for g in groups:
        if g[0] == 'quote':
            quotes, _, _ = mi.get_similar_quotes(g[1])
        elif g[0] == 'source':
            quotes, _, _ = mi.get_source_quotes(g[1])
        elif g[0] == 'person':
            quotes, _, _ = mi.get_person_quotes(g[1])
        elif g[0] == 'keyword':
            quotes, _, _ = mi.get_keyword_quotes_cached(g[1])
        grouplists.append([q.id for q in quotes])
    allquotes = [q for l in grouplists for q in l]
    allquotes = list(set(allquotes))
    coords = mi.get_vis_coords(allquotes)
    quotecoords = dict(zip(allquotes, coords))
    resp_array = []
    for i in range(len(groupstrings)):
        for j in range(len(grouplists[i])):
            qid = grouplists[i][j]
            resp_array.append({
                'group': groupstrings[i],
                'quote': qid,
                'coords': quotecoords[qid].tolist()
            })
    response = {'coords': resp_array}
    return jsonify(response)


@app.route('/person_search/<query>')
def get_person_suggestions(query):
    people = mi.get_person_suggestions(query)
    people = [{'value': p.name, 'id': p.id} for p in people]
    return jsonify(people)


@app.route('/source_search/<query>')
def get_sources_suggestions(query):
    sources = mi.get_source_suggestions(query)
    sources = [{'value': s.source, 'id': s.id} for s in sources]
    return jsonify(sources)


@app.route('/quote_search/<query>')
def get_quote_suggestions(query):
    quotes = mi.get_quote_suggestions(query)
    quotes = [{'value': q.quote, 'id': q.id} for q in quotes]
    return jsonify(quotes)

if __name__ == '__main__':
    host = "0.0.0.0"
    port = 5000
    app.run(host=host, port=port)
