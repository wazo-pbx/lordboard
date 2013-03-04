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

function refreshData() {
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

$(function() {
    refreshData();
    setInterval(refreshData, 10000);
});
