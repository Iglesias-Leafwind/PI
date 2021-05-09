let picker = document.getElementById('picker');
    let listing = [];

    picker.addEventListener('change', e => {
      for (let file of Array.from(e.target.files)) {
        listing.push(file.webkitRelativePath);
      };
    });

$('.savebtn').click(function() {
    $.ajax({
        type: "POST",
        dataType: "json",
        data: {"folder": listing},

        success: function(data) {
            alert('ok')
        }
    })
});
