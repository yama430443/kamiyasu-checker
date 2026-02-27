$(function() {
    // allActors は index.html 内で定義されている純粋な文字列配列を利用
    $("#seiyuu_input").autocomplete({
        source: function(request, response) {
            var term = request.term;
            var matcher = new RegExp($.ui.autocomplete.escapeRegex(term), "i");
            
            // 無駄の排除: kana判定を削除し、単純な文字列マッチに変更
            var results = $.grep(allActors, function(item) {
                return matcher.test(item);
            });
            response(results.slice(0, 20));
        },
        minLength: 1,
        delay: 200
        // 不要になったハック（closeイベントの制御等）は全削除
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