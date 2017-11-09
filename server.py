from flask import Flask, request, render_template, jsonify
from model_interface import ModelInterface
from db import Quote, Source, Person, Session
from sqlalchemy.orm.exc import NoResultFound
import re


app = Flask(__name__)

mi = ModelInterface('models/docvecs',
                    'similarities/dbow300_normed.index')

@app.route('/')
@app.route('/index')
def index():
    return render_template('quote2vec.html')

@app.route('/testing')
def testing():
    returnstr = ''
    for q in mi.get_quotes('Abraham Lincoln'):
        returnstr = returnstr + '\n' + str(q)
    return returnstr

@app.route('/person/<int:id>')
def get_person(id):
    session = Session()
    person = (session.query(Person)
              .filter(Person.id == id)
              .one())
    response = {'name': person.name,
                'id': person.id}
    return jsonify(response)

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


if __name__ == '__main__':
    host = "0.0.0.0"
    port = 5000
    app.run(debug=True, host=host, port=port)
