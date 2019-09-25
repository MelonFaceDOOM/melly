$('.post_footer_bar').on('click', 'img', function() {
    var post_id = $(this).parent().parent().parent().attr('post_id');
    var reaction_type = $(this).parent().parent().attr('name');
    if ($(this).hasClass('unReact')) {
        var unReact = true;
    } else {
        var unReact = false;
    }
    $.ajax({
        url : "/reactions",
        type : 'POST',
        data : {post_id: post_id, reaction_type: reaction_type, unReact: unReact},
        success: function(response) {
            $('#reactions'+post_id).html(response);
        }
    });
});