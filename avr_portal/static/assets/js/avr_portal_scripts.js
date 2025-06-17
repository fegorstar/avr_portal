setTimeout(function() {
    $('#message').fadeOut('slow');
  }, 5000);


        // Handling CSV file upload...
        var regex = new RegExp("(.*?)\.(csv)$");
        function triggerValidation(el) {
          if (!(regex.test(el.value.toLowerCase()))) {
            el.value = '';
            alert('Please select correct file format!');
          }
        }


    