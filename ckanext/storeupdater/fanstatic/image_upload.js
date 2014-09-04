(function()  {
    var default_style = 'inline-block'
    var hidden_style = 'none'

    function readImage(input) {
        if (input.files && input.files[0]) {
            var fr= new FileReader();
            fr.onload = function(e) {
                binary_content = btoa(e.target.result)
                $('#field-image-base64').val(binary_content);
                $('#button-upload').css('display', hidden_style);
                $('#button-remove').css('display', default_style);
            };       
            fr.readAsBinaryString(input.files[0]);
        }
    }

    $('#field-image-upload').change(function(){
        readImage(this);
    });

    $('#button-remove').on('click', function(){
        $('#field-image-base64').val('');
        $('#button-upload').css('display', default_style);
        $('#button-remove').css('display', hidden_style);
    });


    $('#button-upload').on('click', function() {
         $('#field-image-upload').click();
    })
})();
