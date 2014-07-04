var refreshTimer = null;
var matrixTimer = null;
var drawMatrix = null;

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

        checkForMatrix(data);
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

function checkForMatrix(data) {
    var executed = data.stats.passed + data.stats.failed + data.stats.blocked;
    var waiting = data.stats.total - executed;

    if (waiting == 42 && drawMatrix == null) {
        setupMatrix();
        runMatrix();
    } else if (waiting != 42 && drawMatrix != null) {
        stopMatrix();
        removeMatrix();
    }
}

function setupMatrix() {
    //original code found at http://www.arungudelli.com/html5/matrix-effect-using-html5-and-javascript/
    var matrix = $('<canvas id="matrix" width="500" height="400" style="border: 1px solid #c3c3c3;"></canvas>"');
    $('#remaining').append(matrix);

    var canvas = matrix[0];
    var screen = window.screen;
    var width = canvas.width = screen.width;
    var height = canvas.height;
    var ctx = canvas.getContext('2d');
    var yPositions = Array(300).join(0).split('');

    drawMatrix = function() {
        ctx.fillStyle='rgba(0,0,0,.05)';
        ctx.fillRect(0,0,width,height);
        ctx.fillStyle='#0F0';
        ctx.font = '10pt Georgia';

        yPositions.map(function(y, index){
            text = String.fromCharCode(1e2+Math.random()*33);
            x = (index * 10)+10;
            ctx.fillText(text, x, y);

            if(y > 100 + Math.random()*1e4) {
                yPositions[index]=0;
            } else {
                yPositions[index] = y + 10;
            }
        });
    }
}

function removeMatrix() {
    $('#matrix').remove();
}


function runMatrix() {
    stopMatrix();
    matrixTimer = setInterval(drawMatrix, 33);
}

function stopMatrix() {
    if (matrixTimer != null) {
        clearInterval(matrixTimer);
    }
}

$(function() {
    refresh();
    refreshTimer = setInterval(refresh, REFRESH_TIMEOUT);
});
