$body = $("body");

$(document).on({
    ajaxStart: function() { $body.addClass("loading");    },
     ajaxStop: function() { $body.removeClass("loading"); }
});

$(document).ready(function(){
    $('#inputCep').val(localStorage.getItem("cep"));
    $('#inputNumber').val(localStorage.getItem("number"));

});


$('#form').submit(function(event){
    event.preventDefault();
    var data = $('form').serialize();
    var jqxhr = $.post( "get_data",
    data,

     function(result) {
        localStorage.setItem("number",$('#inputNumber').val())
        localStorage.setItem("cep",$('#inputCep').val())
        $('table tbody tr').remove()


        for (var i=0; i<result.data.length; i++){
            var tr=$('<tr>');
            td = $('<td>').html(i+1);
            tr.append(td);
            td = $('<td>').html(result.data[i].name);
            tr.append(td);
            td = $('<td>').html('R$' + result.data[i].pedidoMinimo.toFixed(2).replace(/\d(?=(\d{3})+\.)/g, '$&,'));
            tr.append(td);
            ie = $('<i>').attr('class','fa fa-search')
            a = $('<a>').attr('href',result.data[i].url).append(ie).attr('target',"_blank").attr('rel',"noopener noreferrer")
            td = $('<td>').append(a);

            tr.append(td);


            $('table tbody').append(tr);
        }
        $('#resultsDiv').removeClass('invisible')
        $('.collapse').collapse('hide')
    })
      .fail(function() {
       $('.collapse').collapse('show')
       $('#resultsDiv').addClass('invisible')

      });

});
