import os
import random
import json
import itertools  # 関数内から先頭へ移動
import networkx as nx
import pandas as pd
from flask import Flask, render_template, request

app = Flask(__name__)

# --- 設定 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(BASE_DIR, 'seiyuu_full_db.csv')
TARGET_CENTER_NODE = "神谷浩史"
MAX_ACTORS_PER_ANIME = 40 

# --- グローバル変数 ---
G = nx.Graph()
ACTOR_DB = {}          
ALL_ACTORS_LIST = []   # 単純な名前のリストに変更
ACTORS_BY_DIST = {}    

def load_data():
    global G, ACTOR_DB, ALL_ACTORS_LIST, ACTORS_BY_DIST
    print("システム起動: データを読み込んでいます...")

    if not os.path.exists(CSV_FILE):
        return

    try:
        df = pd.read_csv(CSV_FILE)
        
        # 無駄の排除: カラム探索を廃止し、直接 'Role' を指定
        df['Role'] = df['Role'].fillna('役名なし')

        # 無駄の排除: Kana処理を全削除し、単純な一次元配列を作成
        ALL_ACTORS_LIST = sorted(df['Actor'].dropna().unique().tolist())

        # データベース & グラフ構築
        ACTOR_DB = {}
        grouped_roles = df.groupby(['Actor', 'Anime'])['Role'].apply(
            lambda x: ' / '.join(sorted(set(x.astype(str))))
        )
        for (actor, anime), role in grouped_roles.items():
            if actor not in ACTOR_DB: ACTOR_DB[actor] = {}
            ACTOR_DB[actor][anime] = role

        G = nx.Graph()
        anime_groups = df.groupby('Anime')['Actor'].unique()
        
        for title, actors in anime_groups.items():
            actors = list(actors)
            if len(actors) > MAX_ACTORS_PER_ANIME:
                actors = actors[:MAX_ACTORS_PER_ANIME]
            if len(actors) > 1:
                G.add_edges_from(itertools.combinations(actors, 2))

        # 距離計算
        if TARGET_CENTER_NODE in G:
            lengths = nx.single_source_shortest_path_length(G, TARGET_CENTER_NODE)
            ACTORS_BY_DIST = {}
            for actor, dist in lengths.items():
                if dist > 0:
                    ACTORS_BY_DIST.setdefault(dist, []).append(actor)

    except Exception as e:
        print(f"エラー: {e}")

load_data()

def get_shared_works(actor1, actor2):
    if actor1 not in ACTOR_DB or actor2 not in ACTOR_DB: return []
    works1, works2 = ACTOR_DB[actor1], ACTOR_DB[actor2]
    common = set(works1.keys()) & set(works2.keys())
    return sorted([
        {'title': t, 'role_u': works1[t], 'role_v': works2[t]}
        for t in common
    ], key=lambda x: x['title'])

def find_path(target):
    if not G or target not in G: return None, f"「{target}」は見つかりませんでした。"
    if target == TARGET_CENTER_NODE: return [], None
    try:
        path = nx.shortest_path(G, source=target, target=TARGET_CENTER_NODE)
        return [{
            "actor1": path[i], "actor2": path[i+1],
            "works": get_shared_works(path[i], path[i+1]) or [{'title':'不明','role_u':'?','role_v':'?'}]
        } for i in range(len(path)-1)], None
    except nx.NetworkXNoPath:
        return None, "繋がりが見つかりませんでした。"

@app.route("/", methods=["GET", "POST"])
def index():
    target_name = request.form.get("seiyuu_name", "") if request.method == "POST" else request.args.get("seiyuu_name", "")
    target_name = target_name.strip().replace("　", " ")
    result, error = (find_path(target_name) if target_name else (None, None))

    example_groups = {}
    if ACTORS_BY_DIST:
        for d in [1, 2, 3]:
            if d in ACTORS_BY_DIST:
                cands = ACTORS_BY_DIST[d]
                example_groups[str(d)] = random.sample(cands, min(len(cands), 5))
        
        dist_4_plus = [actor for d, actors in ACTORS_BY_DIST.items() if d >= 4 for actor in actors]
        if dist_4_plus:
            dist_4_plus = list(set(dist_4_plus))
            example_groups["4以上"] = random.sample(dist_4_plus, min(len(dist_4_plus), 5))

    # render_template_string を render_template に変更し、HTMLファイルを呼び出す
    return render_template("index.html", 
                           target_name=target_name, result=result, error=error,
                           example_groups=example_groups,
                           all_actors_json=json.dumps(ALL_ACTORS_LIST))

if __name__ == "__main__":
    app.run(debug=True, port=5000)