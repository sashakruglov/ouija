function plotGraph(datasets, data_platform) {
  var choiceContainer = $("#choices"),
      options = {
        xaxis: {mode: "time", tickLength: 10},
        yaxes:[{min : 0}, {alignTicksWithAxis: 1, position: 'right'}],
        points: {show: true},
        selection: {mode: "x"},
        lines:{fill: false},
        grid: {markings: weekendAreas}
      };

  choiceContainer.find("input").click(plotAccordingToChoices);

  // This function is used to highlighting the weekends in the graph
  function weekendAreas(axes) {
    var markings = [],
        day = 24 * 60 * 60 * 1000,
        d = new Date(axes.xaxis.min),
        i = d.getTime();

    // go to the first Saturday
    d.setUTCDate(d.getUTCDate() - ((d.getUTCDay() + 1) % 7));
    d.setUTCSeconds(0);
    d.setUTCMinutes(0);
    d.setUTCHours(0);

    // when we don't set yaxis, the rectangle automatically
    // extends to infinity upwards and downwards
    do {
        markings.push({ xaxis: { from: d.getTime(), to: i + 2 * day }});
        i += 7 * day;
    } while (i < axes.xaxis.max);

    return markings;
  }

  function renderDates(dates) {
    $(".reportDates").show();
    $("#startDate").text(dates.start_date.split(" ")[0]);
    $("#endDate").text(dates.end_date.split(" ")[0]);
  }

  function plotAccordingToChoices() {
    var data = [];
    choiceContainer.find("input:checked").each(function() {
      var key = $(this).val(),
          platformName = $("label[for='id" + key + "']").text();
      if ( key && datasets[key] ) {
        data.push(datasets[key].data[0]);
        data.push(datasets[key].data[1]);
      }

      renderDates(data_platform[key].dates);
      $('#heading').text(platformName);

    });

    if (data.length > 0) {
      $.plot('#graph', data, options);
    }
  }

  plotAccordingToChoices();
}
