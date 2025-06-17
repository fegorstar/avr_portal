$(document).ready(function(){
$('#clientdelete_btn').click(function(){
    //var formData = $('#algolia-doc-search').val();
    if(confirm("Are you sure want to delete this item?")){
        var id = [];
        var csrf=$('input[name=csrfmiddlewaretoken]').val()
        // $('[name="csrfmiddlewaretoken"]').val()
        // const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        $(':checkbox:checked').each(function(i){
            id[i]=$(this).val();
        })
        if(id.length ===0){
            alert("Please select items to delete.")
        }else{
            console.log(id);
            $.ajax({
                url:'/clientdeletebulkjobs/', //URL FROM THE BASE URL IN URLS IN MAIN URLS.PY FILE
                method:"POST",
                data:{
                    id,
                    // csrfmiddlewaretoken:csrftoken
                    'csrfmiddlewaretoken': csrf,
                },
                success:function(response){
                    for(var i=0; i<id.length;i++){
                        $('tr#'+id[i]+'').css('background-color', '#ccc');
                        $('tr#'+id[i]+'').fadeOut('show');
                        $("#displaysuccessofbulkdelete").fadeIn('slow', function(){
                            $("#displaysuccessofbulkdelete").html('<div class="alert alert-success col-md-4">The Jobs were Successfully Deleted!</div>');
                            $("#displaysuccessofbulkdelete").fadeOut(5000);
                        });
                       
                    }
                }
            })

        
        }

    }

    
}) 

$(document).ready(function(){
    $('#bulkpublish_btn').click(function(){
    //var formData = $('#algolia-doc-search').val();
    if(confirm("Are you sure want to publish this jobs?")){
        var id = [];
        var csrf=$('input[name=csrfmiddlewaretoken]').val()
        // $('[name="csrfmiddlewaretoken"]').val()
        // const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        $(':checkbox:checked').each(function(i){
            id[i]=$(this).val();
        })
        if(id.length ===0){
            alert("Please select items to delete.")
        }else{
            console.log(id);
            $.ajax({
                url:'/clientpublishbulkjobs/', //URL FROM THE BASE URL IN URLS IN MAIN URLS.PY FILE
                method:"POST",
                data:{
                    id,
                    // csrfmiddlewaretoken:csrftoken
                    'csrfmiddlewaretoken': csrf,
                },
                success:function(response){
                    for(var i=0; i<id.length;i++){
                        $('tr#'+id[i]+'').css('background-color', '#ccc');
                        $('tr#'+id[i]+'').fadeOut('show');
                        location.reload()
                       
                    }
                }
            })

        
        }

    }
    

})

})})
