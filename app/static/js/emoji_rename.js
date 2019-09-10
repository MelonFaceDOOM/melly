function rename_emoji(emoji_id, new_name) {
    $.ajax({
        url : "/rename_emoji",
        type : 'POST',
        data: {emoji_id: emoji_id,
                new_name: new_name},
    });

}

$('.emoji-name-field').keyup(function(e) {
    var emoji_id = $(this).attr('emoji_id');
    var new_name = $(this).val()
    if (e.keyCode == 13) {
        rename_emoji(emoji_id, new_name)
    }
});

$('.emoji-name-field').on('blur', function(e) {
    var emoji_id = $(this).attr('emoji_id');
    var new_name = $(this).val()
    rename_emoji(emoji_id, new_name)
});