$(document).ready(function () {
    $("#editTag").click(divClicked); //calls the function on button click
})

function divClicked() {
    alert("hey");
    var divHtml = $(this).prev('div').html(); //select's the contents of div immediately previous to the button
    var editableText = $("<textarea />");
    editableText.val(divHtml);
    $(this).prev('div').replaceWith(editableText); //replaces the required div with textarea
    editableText.focus();
    // setup the blur event for this new textarea
    editableText.blur(editableTextBlurred);
}

function editableTextBlurred() {
    var html = $(this).val();
    var viewableText = $("<div>");
    viewableText.html(html);
    $(this).replaceWith(viewableText);
    // setup the click event for this new div
    viewableText.click(divClicked);
}






