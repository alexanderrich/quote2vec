
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

Coords = Backbone.Model.extend({
    defaults: {'coords': []}
});


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
    initialize: function () {
        this.id = "quotediv" + this.model.id;
        this.template = _.template($("#quote-template").html());
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


Scatter = function (element, data) {

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

    console.log(data);
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
                quote = ql.get(d.quote);
                popupview = new QuoteView({model: quote, className: 'popup', el: $("#popup")});
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

PlotView = Backbone.View.extend({
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


$(document).ready(function() {

    coords = new Coords({coords: []});
    group = new Group({id: 'person8681'});
    view = new GroupView({el: $("#quotelist-container"), model: group});
    group.fetch({success: function () {
        view.render();
    }});

    plotview = new PlotView({el: $("#svg"), model: coords});
    plotview.render();


    $.ajax({
        dataType: "json",
        url: "/coords/person8681",
        success: function (data) {
            coords.set("coords", data.coords);
        }
    });
});
