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

function refreshRemaining() {
    $.getJSON('/stats.json', function(data) {
        var waiting = data.total_manual - data.total_executed;

        $('#executed').html(data.total_executed);
        $('#total').html(data.total_manual);
        $("#waiting").html(waiting);

        $('.passed').html(data.statuses.passed);
        $('.failed').html(data.statuses.failed);
        $('.blocked').html(data.statuses.blocked);

        var failedContainer = $(".failed_list");
        fillTestList(failedContainer, data.lists.failed);

        var blockedContainer = $(".blocked_list");
        fillTestList(blockedContainer, data.lists.blocked);
    });
}

function deactivateRemaining() {
    clearInterval(timeoutId);
    $('#remaining').hide();
}

function deactivateScoreboard() {
    clearInterval(timeoutId);
    $('#scoreboard').hide();
}

function activateRemaining() {
    $('#remaining').slideDown();
    refreshRemaining();
    timeoutId = setInterval(refreshRemaining, REFRESH_TIMEOUT);
}

function activateScoreboard() {
    $('#scoreboard').slideDown();
    refreshScoreboard();
    timeoutId = setInterval(refreshScoreboard, REFRESH_TIMEOUT);
}

function showRemaining() {
    $('#link-scoreboard').parent().removeClass('active');
    deactivateScoreboard();
    activateRemaining();
    $('#link-remaining').parent().addClass('active');
}

function showScoreboard() {
    $('#link-remaining').parent().removeClass('active');
    deactivateRemaining();
    activateScoreboard();
    $('#link-scoreboard').parent().addClass('active');
}

function togglePages() {
    if ( $('#remaining').is(':hidden') ) {
        showRemaining();
    } else {
        showScoreboard();
    }
}

$(function() {
    showRemaining();
    pageTimeoutId = setInterval(togglePages, PAGE_TIMEOUT);

    $('#link-remaining').click(function() {
        clearInterval(pageTimeoutId);
        showRemaining();
        pageTimeoutId = setInterval(togglePages, PAGE_TIMEOUT);
    });

    $('#link-scoreboard').click(function() {
        clearInterval(pageTimeoutId);
        showScoreboard();
        pageTimeoutId = setInterval(togglePages, PAGE_TIMEOUT);
    });

});
