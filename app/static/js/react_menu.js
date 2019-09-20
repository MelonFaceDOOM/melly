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
    $('.emojiSearch[post_id="' + post_id + '"]').focus();
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

//closes popover when clicking away, from:
//https://stackoverflow.com/questions/11703093/how-to-dismiss-a-twitter-bootstrap-popover-by-clicking-outside
$(document).on('click', function (e) {
    $('[data-toggle="popover"],[data-original-title]').each(function () {
        //the 'is' for buttons that trigger popups
        //the 'has' for icons within a button that triggers a popup
        if (!$(this).is(e.target) && $(this).has(e.target).length === 0 && $('.popover').has(e.target).length === 0) {
            (($(this).popover('hide').data('bs.popover')||{}).inState||{}).click = false  // fix for BS 3.3.6
        }
    });
});