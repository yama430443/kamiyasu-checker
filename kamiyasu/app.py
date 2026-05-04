import os
import random
import json
import pickle
import uuid
import threading
from datetime import datetime, timedelta
import networkx as nx
from flask import Flask, render_template, request, session, redirect, url_for
from supabase import create_client, Client

app = Flask(__name__)

# --- セキュリティとセッション設定 ---
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "super_secret_key_for_thesis")
# ブラウザを閉じてもA/Bグループを保持するため有効期限を30日に設定
app.permanent_session_lifetime = timedelta(days=30)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PICKLE_FILE = os.path.join(BASE_DIR, 'app_data.pkl')
TARGET_CENTER_NODE = "神谷浩史"

# --- Supabaseの初期化 ---
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

# --- 事前計算済みデータの読み込み ---
print("計算済みデータを読み込んでいます...")
with open(PICKLE_FILE, 'rb') as f:
    data = pickle.load(f)

ALL_ACTORS_LIST = data["ALL_ACTORS_LIST"]
ACTOR_DB = data["ACTOR_DB"]
G = data["G"]
ACTORS_BY_DIST = data["ACTORS_BY_DIST"]

def get_shared_works(actor1, actor2):
    if actor1 not in ACTOR_DB or actor2 not in ACTOR_DB: return []
    works1, works2 = ACTOR_DB[actor1], ACTOR_DB[actor2]
    common = set(works1.keys()) & set(works2.keys())
    return sorted([
        {'title': t, 'role_u': works1[t], 'role_v': works2[t]}
        for t in common
    ], key=lambda x: x['title'])

def find_path(source_node, target_node):
    if not G or source_node not in G: return None, f"「{source_node}」は見つかりませんでした。"
    if target_node not in G: return None, f"「{target_node}」は見つかりませんでした。"
    if source_node == target_node: return [], "出発点と目的地が同じです。別の声優を入力してください。"

    try:
        path = nx.shortest_path(G, source=source_node, target=target_node)
        return [{
            "actor1": path[i], "actor2": path[i+1],
            "works": get_shared_works(path[i], path[i+1]) or [{'title':'不明','role_u':'?','role_v':'?'}]
        } for i in range(len(path)-1)], None
    except nx.NetworkXNoPath:
        return None, "2人の間に共演の繋がりは見つかりませんでした。"

# --- Supabaseへの非同期ログ送信関数 ---
def insert_log_to_supabase(log_data):
    if not supabase:
        print("Supabase config is missing. Log not sent:", log_data)
        return
    try:
        supabase.table("search_logs").insert(log_data).execute()
    except Exception as e:
        print(f"Supabase insert error: {e}")

# --- 全リクエスト共通：セッション管理とA/Bグループ割り当て ---
@app.before_request
def manage_session():
    # 静的ファイルはセッション処理をスキップ
    if request.path.startswith('/static'):
        return

    session.permanent = True
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
        session['start_time'] = datetime.now().isoformat()
        # 50%の確率で「fixed(固定)」か「free(自由)」を割り当て
        session['assigned_mode'] = 'fixed' if random.random() < 0.5 else 'free'

# --- Aグループ：制約ありモード（神谷浩史数チェッカー） ---
@app.route("/", methods=["GET", "POST"])
def index():
    # freeグループのユーザーは強制リダイレクト
    if session.get('assigned_mode') == 'free':
        return redirect(url_for('search'))

    target_name = request.form.get("seiyuu_name", "") if request.method == "POST" else request.args.get("seiyuu_name", "")
    target_name = target_name.strip().replace("　", " ")
    
    result, error = (find_path(target_name, TARGET_CENTER_NODE) if target_name else (None, None))

    # 検索が実行されたらログを送信
    if target_name:
        log_data = {
            "session_id": session['session_id'],
            "assigned_mode": session['assigned_mode'],
            "start_node": target_name,
            "end_node": TARGET_CENTER_NODE,
            "is_error": bool(error),
            "error_detail": error if error else None,
            "path_length": len(result) if result else 0
        }
        threading.Thread(target=insert_log_to_supabase, args=(log_data,)).start()
    

    return render_template("index.html", 
                           target_name=target_name, result=result, error=error,
                           all_actors_json=json.dumps(ALL_ACTORS_LIST))

# --- Bグループ：制約なしモード（自由検索） ---
@app.route("/search", methods=["GET", "POST"])
def search():
    # fixedグループのユーザーは強制リダイレクト
    if session.get('assigned_mode') == 'fixed':
        return redirect(url_for('index'))

    start_name = request.form.get("start_name", "") if request.method == "POST" else request.args.get("start_name", "")
    end_name = request.form.get("end_name", "") if request.method == "POST" else request.args.get("end_name", "")
    
    start_name = start_name.strip().replace("　", " ")
    end_name = end_name.strip().replace("　", " ")
    
    result, error = None, None
    if start_name and end_name:
         result, error = find_path(start_name, end_name)
    elif start_name or end_name:
         error = "出発点と目的地の両方を入力してください。"

    # 検索が実行されたらログを送信
    if start_name or end_name:
        log_data = {
            "session_id": session['session_id'],
            "assigned_mode": session['assigned_mode'],
            "start_node": start_name,
            "end_node": end_name,
            "is_error": bool(error),
            "error_detail": error if error else None,
            "path_length": len(result) if result else 0
        }
        threading.Thread(target=insert_log_to_supabase, args=(log_data,)).start()

    return render_template("search.html", 
                           start_name=start_name, end_name=end_name, 
                           result=result, error=error,
                           all_actors_json=json.dumps(ALL_ACTORS_LIST))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)