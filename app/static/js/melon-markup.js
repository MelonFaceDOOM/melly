$(document).ready(function() {
    var coll = document.getElementsByClassName("collapsible");
    var i;

    for (i = 0; i < coll.length; i++) {
      coll[i].addEventListener("click", function() {
        this.classList.toggle("active");
        var content = this.nextElementSibling;
        if (content.style.display === "block") {
          content.style.display = "none";
        } else {
          content.style.display = "block";
        }
      });
    }
})

function insertAtCursor(areaId, myValueBefore, myValueAfter) {
    var myField = document.getElementById(areaId);
    if (document.selection) {

        myField.focus();
        document.selection.createRange().text = myValueBefore + document.selection.createRange().text + myValueAfter;


    } else if (myField.selectionStart || myField.selectionStart == '0') {

        var startPos = myField.selectionStart;
        var endPos = myField.selectionEnd;
        myField.value = myField.value.substring(0, startPos)+ myValueBefore+ myField.value.substring(startPos, endPos)+ myValueAfter+ myField.value.substring(endPos, myField.value.length);
		myField.focus(); myField.selectionStart = startPos + myValueBefore.length; myField.selectionEnd = endPos + myValueBefore.length;

    }
}

$('#bold-tag').on('click', function() {
    insertAtCursor("post", "[b]", "[/b]");
});

$('#italics-tag').on('click', function() {
    insertAtCursor("post", "[i]", "[/i]");
});

$('#quote-tag').on('click', function() {
    insertAtCursor("post", "[quote]", "[/quote]");
});

$('#spoiler-tag').on('click', function() {
    insertAtCursor("post", "[spoiler]", "[/spoiler]");
});

$('#image-tag').on('click', function() {
    insertAtCursor("post", "[img]", "[/img]");
});

$('#youtube-tag').on('click', function() {
    insertAtCursor("post", "[yt]", "[/yt]");
});