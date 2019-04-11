$(document).ready(function() {

    $('.reactButton').on('click', function() {
        var post_id = $(this).attr('post_id');
        var reaction_type = "like";

        $.ajax({
            url : "/reactions",
            type : 'POST',
            data : {post_id: post_id, reaction_type: reaction_type},
            success: function(response) {
                $('#reactions'+post_id).html(response);
            }
        });
    });
});