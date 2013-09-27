var timeoutId = null;
var pageTimeoutId = null;

var REFRESH_TIMEOUT = 10000;
var PAGE_TIMEOUT = 30000;

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

function refreshStats() {
    $.getJSON('/stats.json', function(data) {
        var waiting = data.total_manual - data.total_executed;

        $('#executed').html(data.total_executed);
        $('#total').html(data.total_manual);
        $("#waiting").html(waiting);
        $('.version').html(data.version);

        $('.passed').html(data.statuses.passed);
        $('.failed').html(data.statuses.failed);
        $('.blocked').html(data.statuses.blocked);

        var failedContainer = $(".failed_list");
        fillTestList(failedContainer, data.lists.failed);

        var blockedContainer = $(".blocked_list");
        fillTestList(blockedContainer, data.lists.blocked);
    });
}

function deactivateStats() {
    clearInterval(timeoutId);
    $('#stats').hide();
}

function deactivateScoreboard() {
    clearInterval(timeoutId);
    $('#scoreboard').hide();
}

function activateStats() {
    $('#stats').slideDown();
    refreshStats();
    timeoutId = setInterval(refreshStats, REFRESH_TIMEOUT);
}

function activateScoreboard() {
    $('#scoreboard').slideDown();
    refreshScoreboard();
    timeoutId = setInterval(refreshScoreboard, REFRESH_TIMEOUT);
}

function showStats() {
    $('#link-scoreboard').parent().removeClass('active');
    deactivateScoreboard();
    activateStats();
    $('#link-stats').parent().addClass('active');
}

function showScoreboard() {
    $('#link-stats').parent().removeClass('active');
    deactivateStats();
    activateScoreboard();
    $('#link-scoreboard').parent().addClass('active');
}

function togglePages() {
    if ( $('#stats').is(':hidden') ) {
        showStats();
    } else {
        showScoreboard();
    }
}

$(function() {
    showStats();
    pageTimeoutId = setInterval(togglePages, PAGE_TIMEOUT);

    $('#link-stats').click(function() {
        clearInterval(pageTimeoutId);
        showStats();
        pageTimeoutId = setInterval(togglePages, PAGE_TIMEOUT);
    });

    $('#link-scoreboard').click(function() {
        clearInterval(pageTimeoutId);
        showScoreboard();
        pageTimeoutId = setInterval(togglePages, PAGE_TIMEOUT);
    });

});
