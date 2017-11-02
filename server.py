from flask import Flask, request, render_template, jsonify
from model_interface import ModelInterface
from db import Quote, Source, Person, Session
from sqlalchemy.orm.exc import NoResultFound
import re


app = Flask(__name__)

mi = ModelInterface('models/docvecs',
                    'similarities/dbow300_withgoogle.index')

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


if __name__ == '__main__':
    host = "0.0.0.0"
    port = 5000
    app.run(debug=True, host=host, port=port)
