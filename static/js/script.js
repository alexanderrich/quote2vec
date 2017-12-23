var colors = d3.scaleOrdinal(d3.schemeCategory10);

var Person = Backbone.Model.extend({
});

var Quote = Backbone.Model.extend({
});

var Source = Backbone.Model.extend({
});

var Keyword = Backbone.Model.extend({
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

var KeywordList = Backbone.Collection.extend({
    model: Keyword
});

var ql = new QuoteList();
var sl = new SourceList();
var pl = new PersonList();
var kl = new KeywordList();

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
        } else if (this.get("groupbasetype") === "quote") {
            resp.basemodel =  ql.get(this.get("groupbaseid"));
        } else {
            resp.basemodel = kl.get(this.get('groupbaseid'));
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
            person = '';
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
            source = source + ' &ndash;';
        } else if (this.model.get('groupbasetype') === 'quote') {
            head = "Quotes similar to";
            person = pl.get(
                this.model.get('basemodel').get('person_id')
            ).get('name');
            quote = this.model.get('basemodel').get('quote');
            if (quote.length > 100) {
                quote = quote.substring(0, 97) + '...';
            }
            quote = '"' + quote + '"';
            quote = quote + ' &ndash;';
        } else {
            head = "Quotes similar to keywords";
            quote = this.model.get('basemodel').get('keywords');
            if (quote.length > 100) {
                quote = quote.substring(0, 97) + '...';
            }
            quote = '"' + quote + '"';
        }
        this.$el.html("");
        this.$el.html(this.template({head: head,
                                     quote: quote.replace(/\n+/g, ' / '),
                                     source: source,
                                     person: person
                                    }));
        var quotediv = this.$el.children('.quoteholder').eq(0);
        if (this.model.get('isnew')) {
            quotediv.hide();
        }
        for(var i = 0; i < this.model.get('quotes').length; i++){
            var quoteview = new QuoteView({
                model: ql.get(this.model.get('quotes')[i])
            });
            quotediv.append(quoteview.$el);
            quoteview.render();
        }
        if (this.model.get('isnew')) {
            this.model.set('isnew', false);
            quotediv.show(400);
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
        'click .group-x': 'removeGroup',
        'mouseover': 'highlightGroup',
        'mouseout': 'unhighlightGroup'
    },
    initialize: function () {
        this.template = _.template($('#grouplist-button-template').html());
    },
    render: function () {
        var quote = '',
            source = '',
            person = '';
        if (this.model.get('groupbasetype') === 'person') {
            person = this.model.get('basemodel').get('name');
        } else if (this.model.get('groupbasetype') === 'source') {
            person = pl.get(
                this.model.get('basemodel').get('person_id')
            ).get('name');
            source = this.model.get('basemodel').get('source');
            if (source.length > 20) {
                source = source.substring(0, 17) + '...';
            }
            source = source + " &ndash;";
        } else if (this.model.get('groupbasetype') === 'quote') {
            person = pl.get(
                this.model.get('basemodel').get('person_id')
            ).get('name');
            quote = this.model.get('basemodel').get('quote');
            if (quote.length > 20) {
                quote = quote.substring(0, 17) + '...';
            }
            quote = '"' + quote + '"';
            quote = quote + " &ndash;";
        } else {
            quote = this.model.get('basemodel').get('keywords');
            if (quote.length > 20) {
                quote = quote.substring(0, 17) + '...';
            }
            quote = 'Keywords: "' + quote + '"';
        }
        this.$el.html(this.template({quote: quote, source: source, person: person}));
        this.$el.css('background-color', colors(this.model.id));
        return this;
    },
    openGroup: function () {
        showGroup(this.model.get('groupbasetype'), this.model.get('groupbaseid'));
    },
    removeGroup: function () {
        this.$el.remove();
        this.unhighlightGroup();
        this.model.get('groupList').remove(this.model);
        updateCoords();
    },
    highlightGroup: function () {
        d3.selectAll('.dot')
            .style('opacity', .3);
        var points = d3.selectAll('.dotgroup_'+this.model.id);
        if (!points.empty()) {
            points.style('opacity', 1)
                .style('stroke', 'black');
        }
    },
    unhighlightGroup: function () {
        d3.selectAll('.dot')
            .style('opacity', .8)
            .style('stroke', null);
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
    attributes: function () {
        return {id: 'quotediv_' + this.model.id};
    },
    events: {
        'click .quote': 'clickQuote',
        'click .source': 'clickSource',
        'click .person': 'clickPerson',
        'mouseover': 'highlightPoint',
        'mouseout': 'unhighlightPoint'
    },
    initialize: function () {
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
                                     quote: this.model.get('quote').replace(/\n+/g, '<br \>')}));
        return this;
    },
    clickQuote: function () {
        var selection = window.getSelection();
        if(selection.toString().length === 0) {
            showGroup('quote', this.model.get('id'));
        }
    },
    clickSource: function () {
        var selection = window.getSelection();
        if(selection.toString().length === 0) {
            showGroup('source', this.model.get('source_id'));
        }
    },
    clickPerson: function () {
        var selection = window.getSelection();
        if(selection.toString().length === 0) {
            showGroup('person', this.model.get('person_id'));
        }
    },
    highlightPoint: function () {
        this.$el.css("background-color", "AliceBlue");
        d3.selectAll('.dot')
            .style('opacity', .3);
        var point = d3.select('.dotquote_'+this.model.id);
        if (!point.empty()) {
            point.style('opacity', 1)
                .style('stroke', 'black');
        }
    },
    unhighlightPoint: function () {
        this.$el.css("background-color", "white");
        d3.selectAll('.dot')
            .style('opacity', .8)
            .style('stroke', null);
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
        zoom = d3.zoom()
            .scaleExtent([.5, 10])
            .on("zoom", zoomed),
        color = colors,
        svg = d3.select(element).append('g').call(zoom),
        points,
        datakey = function(d, i) {return d.group + "_" + d.quote; },
        olddata = data,
        olddatadict = {};

    var rect = svg.append("rect")
        // .attr("width", $('#svg').width())
        // .attr("height", $('#svg').height())
        .attr('width', '100%')
        .attr('height', '100%')
        // .attr('viewbox', '0 0 100 100')
        .style("fill", "None")
        .style("pointer-events", "all");

    var container = svg.append("g");


    xScale.domain([d3.min(data, xValue) - .05, d3.max(data, xValue) + .05]);
    yScale.domain([d3.min(data, yValue) - .05, d3.max(data, yValue) + .05]);

    points = container.selectAll('circle');

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
        container.selectAll('circle').data(data, datakey)
            .call(exitDots)
            .call(updateDots)
            .call(enterDots);
    };

    function zoomed() {
        container.attr("transform", d3.event.transform);
        d3.selectAll('.dot').attr('r', 7/d3.event.transform.k)
            .style('stroke-width', 2/d3.event.transform.k);
    }

    function enterDots(selection){
        var empty = $("#svg").find('.dot').length == 0,
            duration = empty ? 500 : 500,
            delay = empty ? 0 : 500;
        var k = d3.zoomTransform(svg.node()).k;
        selection.enter().append('circle')
            .attr('class', function(d){return 'dot dotgroup_' + d.group +
                                       ' dotquote_' + d.quote; })
            .attr('r', 7/k)
            .attr('cx', xMap)
            .attr('cy', yMap)
            .style('stroke-width', 2/k)
            .style('stroke', null)
            .style('opacity', 0)
            .on('click', function (d) {
                var substrings = d.group.match(/[a-zA-Z]+|[0-9]+/g);
                showGroup(substrings[0], substrings[1]);
                $('.quoteholder').prop({ scrollTop: -30 - $('.groupholder').height() + $('#quotediv_'+d.quote).position().top });
                $('#quotediv_'+d.quote).css("background-color", "AliceBlue");
            })
            .on('mouseover', function(d) {
                $('#quotediv_'+d.quote).css("background-color", "AliceBlue");
                var quote = ql.get(d.quote);
                d3.select(this)
                    .style('stroke', 'black');
                var popupview = new QuoteView({model: quote, className: 'popup', el: $("#innerpopup")});
                if(d3.event.pageY > $(document).height() / 2) {
                    d3.select('#popup')
                        .style('opacity', 1)
                        .style("left", (d3.event.pageX + 10) + "px")
                        .style('bottom', ($(document).height()-d3.event.pageY) + "px");
                } else {
                    d3.select('#popup')
                        .style('opacity', 1)
                        .style("left", (d3.event.pageX + 10) + "px")
                        .style('top', d3.event.pageY + "px");
                }
                popupview.render();
            })
            .on('mouseout', function (d) {
                $('#quotediv_'+d.quote).css("background-color", 'white');
                console.log($('#quotediv_'+d.quote).css("background-color"));
                d3.select(this)
                    .style('stroke', null);
                d3.select('#popup')
                    .style('opacity', 0)
                    .style('top', null)
                    .style('bottom', null);
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
                           isnew: true,
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
            } else if(searchtype === 'quote'){
                $('#searchfield').attr('placeholder',
                                      'Search quotes');
            } else {
                $('#searchfield').attr('placeholder',
                                       'Search any text');
                $("#randombtn").prop("disabled", true);
            }
            if (searchtype !== 'keywords') {
                build_typeahead(suggestions[searchtype]);
                $("#randombtn").prop("disabled", false);
            }
        }
    });

    build_typeahead(suggestions['person']);

    $('#searchfield').keypress(function(event){
        var keycode = (event.keyCode ? event.keyCode : event.which),
            val = this.value;
        if(keycode == '13' && searchtype === 'keywords'){
            $.ajax({method: 'POST',
                    dataType: 'json',
                    contentType: "application/json; charset=utf-8",
                    url: '/keywords',
                    data: JSON.stringify({keywords: val}),
                    success: function (data) {
                        console.log(data);
                        console.log('keyword' + data.keyword_id);
                        var group;
                        kl.add(new Keyword({id: data.keyword_id, keywords: val}));
                        group = new Group({id: 'keyword' + data.keyword_id,
                                           groupbasetype: 'keyword',
                                           groupbaseid: data.keyword_id,
                                           isnew: true,
                                           groupList: gl});
                        group.set(group.parse(data));
                        showGroup('keyword', data.keyword_id);
                    }
                   });
            this.value = '';
        }
    });

    $('#searchfield').bind('typeahead:select', function(ev, suggestion) {
        showGroup(searchtype, suggestion.id);
        $('#searchfield').typeahead('destroy');
        $('#searchfield').val('');
        var chosen = $('.btn-group label.active input').attr('id');
        if(searchtype !== 'keywords') {
            build_typeahead(suggestions[searchtype]);
        }
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

    $('#instructionsModal').modal('show');
});
