$('.select-choose-category').on("change", function() {
    if (this.value!="Move thread to"){
        $.ajax({
            url : "/move_thread",
            type : 'POST',
            data: {thread_id: $(this).attr('thread_id'),
                    new_name: this.value},
            success: function(response) {
                window.location.href = response;
            }
        });
    }
});

function rename_thread(thread_id, new_name) {
    $.ajax({
        url : "/rename_thread",
        type : 'POST',
        data: {thread_id: thread_id,
                new_name: new_name}
    });
}

$('.manage-thread-field').keyup(function(e) {
    var thread_id = $(this).attr('thread_id');
    var new_name = $(this).val()
    if (e.keyCode == 13) {
        rename_thread(thread_id, new_name)
    }
});

$('.manage-thread-field').on('blur', function(e) {
    var thread_id = $(this).attr('thread_id');
    var new_name = $(this).val()
    rename_thread(thread_id, new_name)
});