function fillScoreboard(container, leaderboard) {
    container.empty();

    $.each(leaderboard.scores, function(key, person) {
        var row = $("<tr/>");
        $("<td/>").html(person.name).appendTo(row);
        $("<td/>").html(person.executed).appendTo(row);

        var percentage = parseInt((person.executed / leaderboard.total) * 100);
        var progress = $("<div/>").addClass('progress');
        var bar = $("<div/>").addClass('bar').css('width', percentage+"%");

        progress.append(bar);
        row.append(progress);
        $("<td/>").append(progress).appendTo(row);

        container.append(row);
    });
}

function refreshScoreboard() {
    $.getJSON('/leaderboard.json', function(data) {
        var container = $(".scores");
        fillScoreboard(container, data);
    });
}

$(function() {
    refreshScoreboard();
    setInterval(refreshScoreboard, 10000);
});
