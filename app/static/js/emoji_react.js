<script>
$('.reactButton').on('click', function() {
    var post_id = $(this).attr('post_id');
    var reaction_type = "like";

    $.ajax({
        url : "{{ url_for('main.reactions') }}",
        type : 'POST',
        data : {post_id: post_id, reaction_type: reaction_type},
        success: function(response) {
            $("#post_footer_reactions").html(response);
        },
        error: function(xhr) {
            //handle error
        }
    });
});
</script>


//        req = $.ajax({
//            url : "{{ url_for('main.reactions') }}",
//            type : 'POST',
//            data : { post_id : post_id, reaction_type : reaction_type }
//        });
//
//        req.done(function() {
//            $('')
//        })
//    })
//
//})