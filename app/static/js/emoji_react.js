$('.post_footer_button').on('click', 'img', function() {
    var post_id = $(this).parent().parent().parent().parent().attr('post_id');
    var reaction_type = $(this).parent().parent().attr('name');
    $.ajax({
        url : "/reactions",
        type : 'POST',
        data : {post_id: post_id, reaction_type: reaction_type},
        success: function(response) {
            $('#reactions'+post_id).html(response);
        }
    });
});