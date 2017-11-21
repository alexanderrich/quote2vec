var colors = d3.scaleOrdinal(d3.schemeCategory10);

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

var coords;

var Group = Backbone.Model.extend({
    urlRoot: 'group',
    defaults: {
        groupList: null
    },
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
    events: {
        'click #addcoords': 'addCoords'
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
            if (source.length > 100) {
                source = source.substring(0, 97) + '...';
            }
        } else {
            head = "Quotes similar to";
            person = pl.get(
                this.model.get('basemodel').get('person_id')
            ).get('name');
            quote = this.model.get('basemodel').get('quote');
            if (quote.length > 100) {
                quote = quote.substring(0, 97) + '...';
            }
            quote = '"' + quote + '"';
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
    },
    addCoords: function () {
        this.model.get('groupList').add(this.model);
        updateCoords();
    }
});

var GroupListGroupView = Backbone.View.extend({
    model: Group,
    tagName: 'div',
    className: 'grouplistgroup',
    events: {
        'click .group-name': 'openGroup',
        'click .group-x': 'removeGroup'
    },
    initialize: function () {
        this.template = _.template($('#grouplist-button-template').html());
    },
    render: function () {
        this.$el.html(this.template({info: this.model.id}));
        this.$el.css('background-color', colors(this.model.id));
        return this;
    },
    openGroup: function () {
        showGroup(this.model.get('groupbasetype'), this.model.get('groupbaseid'));
    },
    removeGroup: function () {
        this.$el.remove();
        this.model.get('groupList').remove(this.model);
        updateCoords();
    }
});

var GroupListView = Backbone.View.extend({
    model: GroupList,
    initialize: function () {
        this.listenTo(this.model, 'add', this.addOne);
    },
    render: function () {
        var models = this.model.models;
        this.$el.html("");
        for(var i = 0; i < models.length; i++) {
            var m = new GroupListGroupView({model: models[i]});
            this.$el.append(m.$el);
            m.render();
        }
    },
    addOne: function (group) {
        var m = new GroupListGroupView({model: group});
        this.$el.append(m.$el);
        m.render();
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


var Scatter = function (element, data, colors) {

    var xValue = function(d){ return d.coords[0]; },
        size = _.min([$('#svg').width(), $('#svg').height()]),
        xScale = d3.scaleLinear().range([40, size-40]),
        xMap = function(d) {return xScale(xValue(d));},
        yValue = function(d){ return d.coords[1]; },
        yScale = d3.scaleLinear().range([40, size-40]),
        yMap = function(d) {return yScale(yValue(d));},
        cValue = function(d) {return d.group; },
        color = colors,
        svg = d3.select(element).append('g'),
        points,
        datakey = function(d, i) {return d.group + "_" + d.quote; },
        olddata = data,
        olddatadict = {};

    xScale.domain([d3.min(data, xValue) - .05, d3.max(data, xValue) + .05]);
    yScale.domain([d3.min(data, yValue) - .05, d3.max(data, yValue) + .05]);

    points = svg.selectAll('circle');

    points.data(data, datakey)
        .call(enterDots);

    _.each(data, function (d, i) {
        olddatadict[d.group + '_' + d.quote] = i;
    });

    this.update = function(data) {
        var datadict = {};
        _.each(data, function (d, i) {
            datadict[d.group + '_' + d.quote] = i;
        });
        for (var i = 0; i<2;i++){
            var sum = 0;
            _.each(olddatadict, function (v, k) {
                if(datadict[k]) {
                    sum += data[datadict[k]].coords[i] * olddata[olddatadict[k]].coords[i];
                }
            });
            if (sum < 0) {
                for(var j = 0; j<data.length; j++){
                    data[j].coords[i] = -data[j].coords[i];
                }
            }
        }
        olddata = data;
        olddatadict = datadict;

        xScale.domain([d3.min(data, xValue) - .05, d3.max(data, xValue) + .05]);
        yScale.domain([d3.min(data, yValue) - .05, d3.max(data, yValue) + .05]);
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
        this.scatter = new Scatter(this.el, this.model.get("coords"), colors);
    },
    update: function () {
        this.scatter.update(this.model.get("coords"));
    }
});

function updateCoords() {
    var groupliststring = _.pluck(gl.models, 'id').join('&');
    if (groupliststring){
        $.ajax({
            dataType: "json",
            url: "/coords/" + groupliststring,
            success: function (data) {
                coords.set('coords', data.coords);
            }
        });
    } else {
        coords.set('coords', []);
    }
}


function showGroup(groupbasetype, groupbaseid) {
    var group = gl.findWhere({id: groupbasetype + groupbaseid});
    if (group) {
        view.model = group;
        view.render();
    } else {
        group = new Group({id: groupbasetype + groupbaseid,
                           groupbasetype: groupbasetype,
                           groupbaseid: groupbaseid,
                           groupList: gl});
        group.fetch({success: function () {
            view.model = group;
            view.render();
        }});
    }
}


$(document).ready(function() {
    view = new GroupView({el: $("#quotelist-container")});

    var grouplistview = new GroupListView({el: $("#grouplist-overlay"),
                                           model: gl});
    grouplistview.render();

    coords = new Coords({coords: []});
    var plotview = new PlotView({el: $("#svg"), model: coords});
    plotview.render();


    var bloodhound_maker = function (url_base) {
        return new Bloodhound({
            datumTokenizer: Bloodhound.tokenizers.obj.whitespace('name'),
            queryTokenizer: Bloodhound.tokenizers.whitespace,
            remote: {
                url: url_base + '/%QUERY',
                wildcard: '%QUERY'
            }
        });
    };

    var suggestions = {
        person: bloodhound_maker('/person_search'),
        source: bloodhound_maker('/source_search'),
        quote: bloodhound_maker('/quote_search')
    };

    var searchtype = 'person';

    var build_typeahead = function (source_suggestions) {
        $('#searchfield').typeahead({highlight: true},
                                    {name: 'suggestions',
                                     display: 'value',
                                     source: source_suggestions});
    };

    $('.btn-group label').click(function () {
        if (searchtype !== $(this).attr('id')) {
            searchtype = $(this).attr('id');
            $('#searchfield').typeahead('destroy');
            if(searchtype === 'person') {
                $('#searchfield').attr('placeholder',
                                      'Search people');
            } else if(searchtype === 'source') {
                $('#searchfield').attr('placeholder',
                                      'Search sources');
            } else {
                $('#searchfield').attr('placeholder',
                                      'Search quotes');
            }
            build_typeahead(suggestions[searchtype]);
        }
    });

    build_typeahead(suggestions['person']);


    $('#searchfield').bind('typeahead:select', function(ev, suggestion) {
        showGroup(searchtype, suggestion.id);
        $('#searchfield').typeahead('destroy');
        $('#searchfield').val('');
        var chosen = $('.btn-group label.active input').attr('id');
        build_typeahead(suggestions[searchtype]);
    });

    $('#randombtn').click(function () {
        $.ajax({
            dataType: "json",
            url: "/random/" + searchtype,
            success: function (data) {
                showGroup(searchtype, data.id);
            }
        });
    });
});
