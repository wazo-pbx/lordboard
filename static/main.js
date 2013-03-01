
function refreshData() {
    $.getJSON('/json', function(data) {
        var waiting = data.total_manual - data.total_executed;

        $('#executed').html(data.total_executed);
        $('#total').html(data.total_manual);
        $("#waiting").html(waiting);

        $('.passed').html(data.statuses.passed);
        $('.failed').html(data.statuses.failed);
        $('.blocked').html(data.statuses.blocked);

        var failedUl = $(".failed_list");
        failedUl.empty();

        $.each(data.lists.failed, function(key, val) {
            $("<li/>").html(val).appendTo(failedUl);
        });

        var blockedUl = $(".blocked_list");
        blockedUl.empty();

        $.each(data.lists.blocked, function(key, val) {
            $("<li/>").html(val).appendTo(blockedUl);
        });

    });
}

$(function() {
    refreshData();
    setInterval(refreshData, 10000);
});
