import datetime
import os
import fastf1
import pandas as pd

# スクリプトと同じディレクトリを取得
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
cache_dir = os.path.join(SCRIPT_DIR, 'cache')
os.makedirs(cache_dir, exist_ok=True)
fastf1.Cache.enable_cache(cache_dir)

def format_timedelta(td):
    """PandasのTimedelta（タイム）を m:ss.sss 形式の文字列に変換"""
    if pd.isna(td):
        return "No Time"
    total_seconds = td.total_seconds()
    minutes = int(total_seconds // 60)
    seconds = total_seconds % 60
    return f"{minutes}:{seconds:06.3f}"

def get_top3_str(session):
    """セッションのトップ3（ドライバー略称とタイム）を取得して文字列化"""
    try:
        # 軽量ロード（順位データのみ取得）
        session.load(laps=False, telemetry=False, weather=False, messages=False)
        results = session.results

        if results is None or results.empty:
            return ""

        top3_list = []
        top3 = results.head(3)

        for _, driver in top3.iterrows():
            code = driver['Abbreviation']  # VER, NOR, LEC など

            # タイムの判定（予選はQ3/Q2/Q1、決勝/スプリントはTime等）
            time_val = None
            for col in ['Time', 'Q3', 'Q2', 'Q1']:
                if col in driver and pd.notna(driver[col]):
                    time_val = driver[col]
                    break

            if time_val is not None and isinstance(time_val, pd.Timedelta):
                time_str = format_timedelta(time_val)
            else:
                time_str = "No Time"

            top3_list.append(f"{code} ({time_str})")

        if top3_list:
            return f" ({'・'.join(top3_list)})"
        return ""
    except Exception:
        return ""

def generate_f1_schedule_with_results():
    current_year = datetime.datetime.now().year
    schedule = fastf1.get_event_schedule(current_year, include_testing=False)
    now_utc = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

    txt_lines = []

    for _, event in schedule.iterrows():
        round_num = event['RoundNumber']
        location = event['EventName']
        gp_name = location.replace("Grand Prix", "GP")

        txt_lines.append(f"// 第{round_num}戦 {gp_name}")

        for session_type in ['Session1', 'Session2', 'Session3', 'Session4', 'Session5']:
            session_name = event[f'{session_type}']
            session_date_utc = event[f'{session_type}DateUtc']

            if pd.isna(session_date_utc):
                continue

            # セッション名の日本語表記変換
            name_map = {
                'Practice 1': 'FP1',
                'Practice 2': 'FP2',
                'Practice 3': 'FP3',
                'Qualifying': '予選',
                'Sprint Qualifying': 'スプリント予選',
                'Sprint Shootout': 'スプリント予選',
                'Sprint': 'スプリント',
                'Race': '決勝'
            }
            jp_session_name = name_map.get(session_name, session_name)

            # FP（フリー走行）の場合はスキップ
            if 'FP' in jp_session_name:
                continue

            # 日本時間 (JST +9h) への変換
            session_date_jst = session_date_utc + pd.Timedelta(hours=9)
            month = session_date_jst.month
            day = session_date_jst.day
            
            # 時間がダミー(00:00:00 UTC)かどうかチェック
            if session_date_utc.hour == 0 and session_date_utc.minute == 0:
                time_str = ""
            else:
                time_str = f"{session_date_jst.hour}:{session_date_jst.strftime('%M')} "

            # 終了済みセッションであればリザルトを取得
            results_str = ""
            if session_date_utc < now_utc:
                try:
                    session = fastf1.get_session(current_year, round_num, session_name)
                    results_str = get_top3_str(session)
                except Exception:
                    results_str = ""

            line = f"{month}/{day} {time_str}{gp_name} {jp_session_name}{results_str}"
            txt_lines.append(line)

        txt_lines.append("")  # 空行

    # schedule.txt へ書き出し
    output_path = os.path.join(SCRIPT_DIR, "schedule.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(txt_lines))

    print(f"[SUCCESS] スケジュールとリザルトを {output_path} に出力しました！")

if __name__ == "__main__":
    generate_f1_schedule_with_results()