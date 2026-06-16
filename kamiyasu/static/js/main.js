$(function() {
    const actorsDataText = document.getElementById('actors-data').textContent;
    const allActors = JSON.parse(actorsDataText);

    console.log(allActors);

    // クラス名で複数の入力欄にオートコンプリートを適用
    $("#seiyuu_input, .autocomplete-input").autocomplete({
        source: function(request, response) {
            var term = request.term;
            var matcher = new RegExp($.ui.autocomplete.escapeRegex(term), "i");

            var results = $.grep(allActors, function(item) {
                return matcher.test(item);
            });
            response(results.slice(0, 50));
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


// --- 人間確認ビーコン ---
// JSが実行され、かつ「操作 or 一定時間の滞在」があったセッションだけを
// /confirm に通知し、サーバ側で human_confirmed = true に昇格させる。
// 読み込むだけのBotや投機的プリフェッチは操作しないため除外される。
(function() {
    let fired = false;
    function confirmHuman() {
        if (fired) return;
        fired = true;
        navigator.sendBeacon('/confirm');
    }

    // 何らかの操作で確認（検索・オートコンプリート・作品展開などを含む）
    window.addEventListener('scroll',      confirmHuman, { once: true, passive: true });
    window.addEventListener('pointerdown', confirmHuman, { once: true });
    // 操作がなくても2.5秒滞在すれば人間とみなす（フォールバック）
    setTimeout(confirmHuman, 2500);

    // アンケートボタンのクリックも確認イベントにする
    // （即クリックで離脱する人間のコンバージョンを取りこぼさないため）
    document.querySelectorAll('a.survey-btn').forEach(function(a) {
        a.addEventListener('click', confirmHuman);
    });
})();