
var Person = Backbone.Model.extend({
});

var Quote = Backbone.Model.extend({
});

var Source = Backbone.Model.extend({
});

var QuoteList = Backbone.Collection.extend({
    model: Quote
});

var SourceList = Backbone.Collection.extend({
    model: Source
});

var PersonList = Backbone.Collection.extend({
    model: Person
});

var ql = new QuoteList();
var sl = new SourceList();
var pl = new PersonList();

var Coords = Backbone.Model.extend({
    defaults: {'coords': []}
});


var Group = Backbone.Model.extend({
    urlRoot: 'group',
    parse: function (response) {
        var resp = {quotes: [],
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
        if (this.get("groupbasetype") === "person") {
            resp.basemodel =  pl.get(this.get("groupbaseid"));
        } else if (this.get("groupbasetype") === "source") {
            resp.basemodel =  sl.get(this.get("groupbaseid"));
        } else {
            resp.basemodel =  ql.get(this.get("groupbaseid"));
        }
        return resp;
    }
});

var GroupList = Backbone.Collection.extend({
    model: Group
});

var gl = new GroupList();


var GroupView = Backbone.View.extend({
    model: Group,
    initialize: function () {
        this.template = _.template($('#group-template').html());
    },
    render: function () {
        var head,
            quote = '',
            source = '',
            person;
        if (this.model.get('groupbasetype') === 'person') {
            head = "Quotes by";
            person = this.model.get('basemodel').get('name');
        } else if (this.model.get('groupbasetype') === 'source') {
            head = "Quotes from";
            person = pl.get(
                this.model.get('basemodel').get('person_id')
            ).get('name');
            source = this.model.get('basemodel').get('source');
        } else {
            head = "Quotes similar to";
            person = pl.get(
                this.model.get('basemodel').get('person_id')
            ).get('name');
            quote = this.model.get('basemodel').get('quote');
        }
        this.$el.html("");
        this.$el.html(this.template({head: head,
                                     quote: quote,
                                     source: source,
                                     person: person
                                    }));
        var quotediv = this.$el.children('.quoteholder').eq(0);
        for(var i = 0; i < this.model.get('quotes').length; i++){
            var quoteview = new QuoteView({
                model: ql.get(this.model.get('quotes')[i])
            });
            quotediv.append(quoteview.$el);
            quoteview.render();
        }
        return this;
    }
});


var view;

var QuoteView = Backbone.View.extend({
    model: Quote,
    tagName: "div",
    className: "quotediv",
    events: {
        'click .quote': 'clickQuote',
        'click .source': 'clickSource',
        'click .person': 'clickPerson'
    },
    initialize: function () {
        this.id = "quotediv" + this.model.id;
        this.template = _.template($("#quote-template").html());
    },
    render: function () {
        var person = pl.get(this.model.get('person_id')).get('name');
        var source;
        if (this.model.get('source_id')){
            source = sl.get(this.model.get('source_id')).get('source');
        } else {
            source = "";
        }
        this.$el.html(this.template({person: person,
                                     source: source,
                                     quote: this.model.get('quote')}));
        return this;
    },
    clickQuote: function () {
        showGroup('quote', this.model.get('id'));
    },
    clickSource: function () {
        showGroup('source', this.model.get('source_id'));
    },
    clickPerson: function () {
        showGroup('person', this.model.get('person_id'));
    }
});


var Scatter = function (element, data) {

    var xValue = function(d){ return d.coords[0]; },
        size = _.min([$('#svg').width(), $('#svg').height()]),
        xScale = d3.scaleLinear().range([40, size-40]),
        xMap = function(d) {return xScale(xValue(d));},
        yValue = function(d){ return d.coords[1]; },
        yScale = d3.scaleLinear().range([40, size-40]),
        yMap = function(d) {return yScale(yValue(d));},
        cValue = function(d) {return d.group; },
        color = d3.scaleOrdinal(d3.schemeCategory10),
        svg = d3.select(element).append('g'),
        points,
        datakey = function(d, i) {return d.group + "_" + d.quote; };

    xScale.domain([d3.min(data, xValue), d3.max(data, xValue)]);
    yScale.domain([d3.min(data, yValue), d3.max(data, yValue)]);

    points = svg.selectAll('circle');

    points.data(data, datakey)
        .call(enterDots);


    this.update = function(data) {
        for (var i = 0; i<data.length;i++){
            data[i].coords[0] = data[i].coords[0];
        }

        xScale.domain([d3.min(data, xValue), d3.max(data, xValue)]);
        yScale.domain([d3.min(data, yValue), d3.max(data, yValue)]);
        svg.selectAll('circle').data(data, datakey)
            .call(exitDots)
            .call(updateDots)
            .call(enterDots);
    };

    function enterDots(selection){
        var empty = $("#svg").find('.dot').length == 0,
            duration = empty ? 500 : 500,
            delay = empty ? 0 : 500;
        selection.enter().append('circle')
            .attr('class', 'dot')
            .attr('r', 7)
            .attr('cx', xMap)
            .attr('cy', yMap)
            .style('opacity', 0)
            .on('mouseover', function(d) {
                var quote = ql.get(d.quote);
                var popupview = new QuoteView({model: quote, className: 'popup', el: $("#popup")});
                popupview.render();
                d3.select('#popup')
                    .style('opacity', 1)
                    .style("left", (d3.event.pageX + 10) + "px")
                    .style("top", (d3.event.pageY) + "px");
            })
            .on('mouseout', function () {
                d3.select('#popup')
                    .style('opacity', 0);
            })
            .transition()
            .duration(duration)
            .delay(delay)
            .style('opacity', .8)
            .style('fill', function(d) {return color(cValue(d)); });
    }

    function updateDots(selection){
        selection.transition()
            .duration(1000)
            .attr('cx', xMap)
            .attr('cy', yMap);
    }

    function exitDots(selection){
        selection.exit().transition()
            .duration(500)
            .style('opacity', 0)
            .remove();
    }


};

var PlotView = Backbone.View.extend({
    model: Coords,
    initialize: function () {
        this.listenTo(this.model, 'change', this.update);
    },
    render: function () {
        this.scatter = new Scatter(this.el, this.model.get("coords"));
    },
    update: function () {
        this.scatter.update(this.model.get("coords"));
    }
});


function showGroup(groupbasetype, groupbaseid) {
    var group = gl.findWhere({id: groupbasetype + groupbaseid});
    if (group) {
        view.model = group;
        view.render();
    } else {
        group = new Group({id: groupbasetype + groupbaseid,
                           groupbasetype: groupbasetype,
                           groupbaseid: groupbaseid});
        group.fetch({success: function () {
            view.model = group;
            view.render();
        }});
    }
}

$(document).ready(function() {
    view = new GroupView({el: $("#quotelist-container")});
    // gl.add(group);
    showGroup('person', 1);

    var coords = new Coords({coords: []});
    var plotview = new PlotView({el: $("#svg"), model: coords});
    plotview.render();


    $.ajax({
        dataType: "json",
        url: "/coords/quote1",
        success: function (data) {
            coords.set("coords", data.coords);
        }
    });
});
