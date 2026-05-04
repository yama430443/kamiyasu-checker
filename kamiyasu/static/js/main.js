$(function() {
    const actorsDataText = document.getElementById('actors-data').textContent;
    const allActors = JSON.parse(actorsDataText);

    // クラス名で複数の入力欄にオートコンプリートを適用
    $("#seiyuu_input, .autocomplete-input").autocomplete({
        source: function(request, response) {
            var term = request.term;
            var matcher = new RegExp($.ui.autocomplete.escapeRegex(term), "i");
            
            var results = $.grep(allActors, function(item) {
                return matcher.test(item);
            });
            response(results.slice(0, 30));
        },
        minLength: 1,
        delay: 200
    });
});


function toggleWorks(index) {
    var el = document.getElementById('works-' + index);
    var btn = event.target;
    if (el.style.display === 'block') {
        el.style.display = 'none';
        btn.innerText = '他 ' + (el.children.length) + ' 作品を見る';
    } else {
        el.style.display = 'block';
        btn.innerText = '閉じる';
    }
}