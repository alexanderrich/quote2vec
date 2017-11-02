
    Person = Backbone.Model.extend({
    });

    Quote = Backbone.Model.extend({
    });

    Source = Backbone.Model.extend({
    });

    QuoteList = Backbone.Collection.extend({
        model: Quote
    });

    SourceList = Backbone.Collection.extend({
        model: Source
    });

    PersonList = Backbone.Collection.extend({
        model: Person
    });

    ql = new QuoteList();
    sl = new SourceList();
    pl = new PersonList();

$(document).ready(function() {
    Group = Backbone.Model.extend({
        urlRoot: 'group',
        parse: function (response) {
            resp = {quotes: [],
                    sources: [],
                    people: []
                   };
            response.quotes.forEach(function(i) {
                ql.add(new Quote(i));
                resp.quotes.push(i.id);
            });
            response.sources.forEach(function(i) {
                sl.add(new Source(i));
                resp.sources.push(i.id);
            });
            response.people.forEach(function(i) {
                pl.add(new Person(i));
                resp.people.push(i.id);
            });
            return resp;
        }
    });

    var GroupView = Backbone.View.extend({
        model: Group,
        // initialize: function() {
        //     this.listenTo(this.model, 'all', this.render);
        // },
        render: function () {
            // this.$el.html(this.model.get('quotes').toString());
            this.$el.html("");
            for(var i = 0; i < this.model.get('quotes').length; i++){
                var quoteview = new QuoteView({
                    model: ql.get(this.model.get('quotes')[i])
                });
                this.$el.append(quoteview.$el);
                quoteview.render();
            }
            return this;
        }
    });

    var QuoteView = Backbone.View.extend({
        model: Quote,
        tagName: "div",
        className: "quotediv",
        template: _.template($("#quote-template").html()),
        initialize: function () {
            this.className = "quotediv" + this.model.id;
        },
        render: function () {
            person = pl.get(this.model.get('person_id')).get('name');
            source = sl.get(this.model.get('source_id')).get('source');
            this.$el.html(this.template({person: person,
                                         source: source,
                                         quote: this.model.get('quote')}));
            return this;
        }
    });

    group = new Group({id: 'person800'});
    view = new GroupView({el: $("#quotelist-container"), model: group});
    group.fetch({success: function () {
        view.render();
    }});
});
