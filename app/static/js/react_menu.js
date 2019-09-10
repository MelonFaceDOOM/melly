$(document).ready(function() {
    $('[data-toggle="popover"]').popover({
        html: true,
        content: function() {
            var post_id = $(this).attr('post_id');
            return reaction_menu_page(post_id=post_id);
        }
    });
})

function reaction_menu_page(post_id, page=1) {
    return $.ajax({
        url : "/reaction_menu?page=" + page + "&post_id=" + post_id,
        type : 'GET',
        datatype: 'html',
        async: false}).responseText;
}

function change_page(post_id, page=1){
    var reaction_menu = reaction_menu_page(post_id=post_id, page=page);
    $('.reaction_menu[post_id="' + post_id + '"]').parent().html(reaction_menu);
}

$('.emojiSearch').keyup(function(e) {
    clearTimeout($.data(this, 'timer'));
    var post_id = $(this).attr('post_id');
    if (e.keyCode == 13)
      search(post_id);
    else
      $(this).data('timer', setTimeout(search.bind(null, post_id), 250));
});

function search(post_id) {
    var existingString = $('.emojiSearch[post_id="' + post_id + '"]').val();
    if (existingString.length < 1) {
        change_page(post_id);
        return;
    }
    var reaction_menu = $.ajax({
        url : "/search_emojis?search_string=" + existingString + "&post_id=" + post_id,
        type : 'GET',
        datatype: 'html',
        async: false}).responseText;
    $('.emoji-grid[post_id="' + post_id + '"]')[0].outerHTML = reaction_menu;

}