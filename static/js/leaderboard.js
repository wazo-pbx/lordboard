function generateBar(type, executed, total) {
	var percentage = ((executed / total) * 100);
	var bar = $("<div/>")
		.addClass('bar')
		.addClass(type)
		.css('width', percentage+"%");

	return bar;
}


function fillScoreboard(container, leaderboard) {
    container.empty();

    $.each(leaderboard.scores, function(key, person) {
        var row = $("<tr/>");
        $("<td/>").html(person.name).appendTo(row);

		var total_executed = 
			(person.executed.passed || 0) +
			(person.executed.failed || 0) +
			(person.executed.blocked || 0);

        $("<td/>").html(total_executed).appendTo(row);

		var progress = $("<div/>").addClass('progress');

		if (person.executed.passed) {
			var bar = generateBar('bar-success', person.executed.passed, leaderboard.total);
			progress.append(bar);
		}

		if (person.executed.failed) {
			var bar = generateBar('bar-danger', person.executed.failed, leaderboard.total);
			progress.append(bar);
		}

		if (person.executed.blocked) {
			var bar = generateBar('bar-info', person.executed.blocked, leaderboard.total);
			progress.append(bar);
		}

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
