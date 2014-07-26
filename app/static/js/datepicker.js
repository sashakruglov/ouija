$(function() {
  var today = new Date(),
      lastWeek = new Date(
          today.getFullYear(),
          today.getMonth(),
          today.getDate() - 7
      );

  $( '#start_date' ).datepicker({
    defaultDate: '-1w',
    numberOfMonths: 2,
    dateFormat: 'yy-mm-dd',
    maxDate: new Date(),
    onClose: function( selectedDate ) {
      $( '#end_date' ).datepicker( 'option', 'minDate', selectedDate );
    }
  })
  .datepicker('setDate', lastWeek);

  $( '#end_date' ).datepicker({
    numberOfMonths: 2,
    dateFormat: 'yy-mm-dd',
    maxDate: new Date(),
    onClose: function( selectedDate ) {
      $( '#start_date' ).datepicker( 'option', 'maxDate', selectedDate );
    }
  })
  .datepicker('setDate', today);
});
