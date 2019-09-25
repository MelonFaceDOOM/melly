//create popover menu on reactButton press
$(document).ready(function() {
    $('[data-toggle="popover"]').popover({
        html: true,
        content: function() {
            var post_id = $(this).attr('post_id');
            return reaction_menu_page(post_id=post_id);
        }
    });
})

//This will auto-focus the in-menu search bar when the reactButton is clicked
$('[data-toggle="popover"]').on('shown.bs.popover', function() {
    $('.popover').find(".emojiSearch").focus();
});

function react(post_id, reaction_type){
    $.ajax({
        url : "/reactions",
        type : 'POST',
        data : {post_id: post_id, reaction_type: reaction_type, unReact:false},
        success: function(response) {
            $('#reactions'+post_id).html(response);
        }
    });
}

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

// TODO: would it make more sense to enter stuff into the search bar if the user was focusing any part of the menu?
//  also, you definitely want it to close if you user presses esc anywhere in the menu. Currently it will only close
//  if they press esc while specifically in the search bar
$('.emojiSearch').keyup(function(e) {
    clearTimeout($.data(this, 'timer'));
    var post_id = $(this).attr('post_id');
    //submit first result if the user presses enter
    if (e.keyCode == 13) {
        search(post_id);
        var first_result = $(this).parent().children('.emoji-grid').children('.reaction_box').attr('name');
        react(post_id, first_result);
    // close menu on esc
    } else if (e.keyCode == 27){
        // .popover('hide') is the important code here, but the rest prevents a glitch that requires
        // double clicking the menu to re-open after closing
        (($(this).parent().parent().parent().popover('hide').data('bs.popover')||{}).inState||{}).click = false
    } else {
        $(this).data('timer', setTimeout(search.bind(null, post_id), 250));
    }
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


// closes popover when clicking away, from:
// https://stackoverflow.com/questions/11703093/how-to-dismiss-a-twitter-bootstrap-popover-by-clicking-outside
// unfortunately, it also closes if you highlight the text bar and pull the mouse off before releasing lmb
// it also closes the menu when clicking through the pages, so for now i will disable it

//$(document).on('click', function (e) {
//    $('[data-toggle="popover"],[data-original-title]').each(function () {
//        //the 'is' for buttons that trigger popups
//        //the 'has' for icons within a button that triggers a popup
//        if (!$(this).is(e.target) && $(this).has(e.target).length === 0 && $('.popover').has(e.target).length === 0) {
//            (($(this).popover('hide').data('bs.popover')||{}).inState||{}).click = false  // fix for BS 3.3.6
//        }
//    });
//});