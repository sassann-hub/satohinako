"""
family_profile.py — 家族設定の保存・読み込み（担当：けーや）

【このファイルの役割】
  - 画面（app.py）で入力した家族設定を、database.py の save_family() で保存する
  - 保存した家族設定を database.py の get_family() で読み込んで、app.py と filter.py に渡す
  - データベースの値（英語のコード）と、画面に出す日本語の対応表を持つ

【ポイント】
  このアプリは1家族で使う前提なので、families テーブルの id=1 の「1行だけ」を使う。
  1回目の保存は新しく登録（INSERT）、2回目からはその行を上書き（UPDATE）する。
"""

# SQLite とのやり取りは、さっさんの database.py の関数に任せる
from database import get_family, save_family

FAMILY_ID = 1  # 1家族だけで使うので、行の番号は 1 で固定

# データベースの値（英語のコード） → 画面に出す日本語
MEMBER_LABELS = {"papa": "パパ", "mama": "ママ", "child": "子ども"}

# schema.sql の genre の CHECK と同じ5種類
GENRE_LABELS = {
    "character": "キャラクター",
    "experience": "体験",
    "show": "ショー",
    "seasonal": "季節の行事",
    "play": "あそび",
}


def load_profile():
    """保存済みの家族設定を辞書で返す。まだ保存していなければ None を返す。"""
    family = get_family(FAMILY_ID)  # 見つからなければ None
    if family is None:
        return None

    return {
        "members": family["members"],                              # ["papa", "mama", "child"]
        "child_ages": family["child_ages"],                        # [3, 6]
        "has_car": family["has_car"],                              # True / False
        "favorite_character": family["favorite_character"] or "",  # None なら "" にそろえる
        "favorite_genres": family["favorite_genres"],              # ["character", "show"]
    }


def save_profile(profile):
    """家族設定を保存する。まだなければ新しく登録、あれば上書きする。"""
    if get_family(FAMILY_ID) is None:
        save_family(profile)             # 1回目：新しく登録（id は 1 になる）
    else:
        save_family(profile, FAMILY_ID)  # 2回目から：id=1 の行を上書き


def summarize(profile):
    """画面上部に出す一行の説明。例：「パパ・ママ・子ども3歳 ／ 車あり ／ 好き：仮面ライダー」"""
    if profile is None:
        return "家族設定がまだありません"

    # 「子ども」は年齢と一緒に後で足すので、ここではパパ・ママだけ日本語にして集める
    parts = [MEMBER_LABELS.get(m, m) for m in profile["members"] if m != "child"]

    # 子どもがいれば「子ども3歳・6歳」を足す
    if profile["child_ages"]:
        ages = "・".join(f"{a}歳" for a in profile["child_ages"])  # [3, 6] → "3歳・6歳"
        parts.append(f"子ども{ages}")

    car = "車あり" if profile["has_car"] else "車なし"
    text = "・".join(parts) + " ／ " + car

    # 好きなキャラがあれば「／ 好き：仮面ライダー」も足す
    if profile["favorite_character"]:
        text += " ／ 好き：" + profile["favorite_character"]
    return text