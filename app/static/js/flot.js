$(function() {
  var $form = $("form"),
      $body = $("body"),
      $error = $("#error"),
      $dates = $(".reportDates");

  function fetchData(e) {
    if (e) e.preventDefault();
    $.getJSON("/api/flot/", $form.serialize())
      .done(renderResponse)
      .fail(handleError);
  }

  function renderResponse(data) {
    if (data.error) {
      handleError(data.error);
      return;
    }

    if ($error.is(":visible")) $error.hide();

    plotGraph(getDataSets(data), data);
  }

  function handleError(errMsg) {
    if ($.type(errMsg) === "object") {
      errMsg = "Ajax request failed";
    }
    $dates.hide();
    $error.text(errMsg).show();
  }


  // This function is used to convert the data obtained from getData into a format required by flot.
  function getDataSets(data) {
    var datasets = {};

    $.each(data, function(platformName, platformValue) {
      datasets[platformName] = {};
      datasets[platformName].label = platformName;

      var failures = {
        color: 'orange',
        data: platformValue.data.failures,
        label: 'failures' + '-' + platformName,
        lines: { show: true, color: 'orange'},
        yaxis: 2
        };

      var totals = {
        color: 'blue',
        data: platformValue.data.totals,
        label: 'total jobs' + '-' + platformName,
        lines: {show: true, color: 'blue'},
        };

      datasets[platformName].data = [totals, failures];
      });

    console.log(datasets);
    return datasets;
  }

  $dates.hide();
  $form.submit(fetchData);

  $(document).on("ajaxStart ajaxStop", function (e) {
      (e.type === "ajaxStart") ? $body.addClass("loading") : $body.removeClass("loading");
  });

  fetchData();

});
