var refreshTimer = null;

var REFRESH_TIMEOUT = 10000;

function refresh() {
    $.getJSON('/dashboard.json', function(data) {
        $('.version').html(data.version);

        fillStats(data.stats)

        var scoreboard = $(".scores");
        fillScoreboard(scoreboard, data);

        var failed = $(".failed_list");
        fillTestList(failed, data.failed);

        var blocked = $(".blocked_list");
        fillTestList(blocked, data.blocked);
    });
}

function fillStats(stats) {
    var executed = stats.passed + stats.failed + stats.blocked;
    var waiting = stats.total - executed;

    $('#executed').html(executed);
    $('#total').html(stats.total);
    $("#waiting").html(waiting);

    $('.passed').html(stats.passed);
    $('.failed').html(stats.failed);
    $('.blocked').html(stats.blocked);
}

function fillScoreboard(container, dashboard) {
    container.empty();

    $.each(dashboard.testers, function(key, person) {
        var row = $("<tr/>");
        $("<td/>").html(person.name).appendTo(row);

        var total_executed = 
            (person.executed.passed || 0) +
            (person.executed.failed || 0) +
            (person.executed.blocked || 0);

        $("<td/>").html(total_executed).appendTo(row);
        $("<td/>").html(person.last_path).appendTo(row);

        var progress = $("<div/>").addClass('progress');

        if (person.executed.passed) {
            var bar = generateBar('bar-success', person.executed.passed, dashboard.stats.total);
            progress.append(bar);
        }

        if (person.executed.failed) {
            var bar = generateBar('bar-danger', person.executed.failed, dashboard.stats.total);
            progress.append(bar);
        }

        if (person.executed.blocked) {
            var bar = generateBar('bar-info', person.executed.blocked, dashboard.stats.total);
            progress.append(bar);
        }

        row.append(progress);
        $("<td/>").append(progress).appendTo(row);

        container.append(row);
    });
}

function generateBar(type, executed, total) {
    var percentage = ((executed / total) * 100);
    var bar = $("<div/>")
        .addClass('bar')
        .addClass(type)
        .css('width', percentage+"%");
    return bar;
}

function fillTestList(container, tests) {
    container.empty();
    $.each(tests, function(key, test) {
        var element = $("<li/>").html(test.name);
        if (test.notes != "") {
            $("<ul><li class='note'>" + test.notes + "</li></ul>").appendTo(element);
        }
        element.appendTo(container);
    });
}

$(function() {
    refresh();
    refreshTimer = setInterval(refresh, REFRESH_TIMEOUT);
});
