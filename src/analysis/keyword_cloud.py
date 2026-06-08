from __future__ import annotations

import math
import os
import random
import re
import tempfile
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", os.path.join(tempfile.gettempdir(), "matplotlib"))

import matplotlib
matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from matplotlib import patches
from sklearn.feature_extraction.text import CountVectorizer, ENGLISH_STOP_WORDS

plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = [
    "Hiragino Sans",
    "Yu Gothic",
    "Noto Sans CJK JP",
    "IPAexGothic",
    "TakaoGothic",
    "DejaVu Sans",
]


KEYWORD_STOPWORDS = set(ENGLISH_STOP_WORDS) | {
    "actually", "also", "amazing", "area", "around", "beautifully", "better",
    "came", "definitely", "did", "does", "don", "early", "enjoy", "excellent",
    "experience", "feel", "felt", "free", "good", "google", "great", "highly",
    "inside", "interesting", "it's", "just", "like", "little", "local", "lot",
    "lots", "love", "loved", "main", "make", "nice", "people", "perfect",
    "pretty", "quite", "recommend", "recommended", "really", "review", "right",
    "small", "spot", "stop", "super", "sure", "temple", "things", "think",
    "time", "traditional", "ve", "way", "went", "worth",
}

GENERIC_SINGLE_TERMS = {
    "attraction", "attractions", "building", "buildings", "city", "japan",
    "japanese", "museum", "peaceful", "place", "places", "quiet", "temple",
    "tourist", "travel", "trip", "visit", "visited", "visiting",
}

TOKEN_RE = re.compile(r"(?u)\b[a-zA-Z][a-zA-Z&'/-]{2,}\b")
LOW_SIGNAL_PATTERNS = (
    re.compile(r"^[a-z]$"),
    re.compile(r"^(https?|www)$"),
)
PALETTE = ["#FF2D2D", "#FF5A36", "#FF7A00", "#24B35B", "#245CFF", "#7A2BFF", "#E91E63"]
CANONICAL_TERM_MAP = {
    "castles": "castle",
    "cliffs": "cliff",
    "don't": "",
    "exhibits": "exhibit",
    "grounds": "ground",
    "knives": "knife",
}

CATEGORY_DEFINITIONS = [
    {
        "label": "Scenic Spots & Landscapes",
        "keywords": [
            "beautiful", "view", "views", "scenic", "scenery", "landscape", "panorama",
            "garden", "grounds", "picturesque", "sunset", "cherry blossom", "autumn",
            "foliage", "snow",
        ],
        "poi_categories": ["nature_scenic"],
    },
    {
        "label": "Temples & Spiritual Heritage",
        "keywords": [
            "zen", "spiritual", "serene", "buddhist", "buddha", "prayer", "sacred",
            "shrine", "eiheiji", "daibutsu", "meditation", "monk", "monks", "heritage",
        ],
        "poi_categories": ["temple_shrine"],
    },
    {
        "label": "Castles & Historic Landmarks",
        "keywords": [
            "castle", "historic", "history", "samurai", "keep", "moat", "tower",
            "landmark", "red brick", "warehouse", "gate", "oldest",
        ],
        "poi_categories": ["castle_historic"],
    },
    {
        "label": "Dinosaurs & Museums",
        "keywords": [
            "dinosaur", "dinosaurs", "fossil", "fossils", "museum", "museums", "exhibit",
            "replica", "paleontology", "skeleton", "skeletons", "educational",
        ],
        "poi_categories": ["museum_cultural"],
    },
    {
        "label": "Food & Local Cuisine",
        "keywords": [
            "food", "crab", "soba", "seafood", "restaurant", "cuisine", "dish", "dishes",
            "delicious", "lunch", "dinner", "meal", "ramen", "noodle", "sake", "market",
        ],
        "poi_categories": [],
    },
    {
        "label": "Nature & Coast",
        "keywords": [
            "sea", "coast", "coastal", "ocean", "shore", "cliff", "cliffs", "river",
            "island", "beach", "waves", "breeze", "nature", "promenade",
        ],
        "poi_categories": ["nature_scenic"],
    },
    {
        "label": "Photography & Seasonal Beauty",
        "keywords": [
            "photo", "photos", "photography", "photograph", "pictures", "instagram",
            "blossom", "blossoms", "autumn leaves", "foliage", "snow", "sunset",
        ],
        "poi_categories": [],
    },
    {
        "label": "Shopping & Local Crafts",
        "keywords": [
            "knife", "knives", "washi", "pottery", "craft", "crafts", "shopping",
            "souvenir", "souvenirs", "artisan", "artisans", "market", "village",
        ],
        "poi_categories": ["market_shopping"],
    },
    {
        "label": "Access & Visitor Logistics",
        "keywords": [
            "access", "bus", "train", "parking", "ticket", "tickets", "fee", "fees",
            "crowded", "queue", "line", "wait", "english", "sign", "signs", "directions",
            "shuttle", "transport", "transportation", "drive",
        ],
        "poi_categories": [],
    },
    {
        "label": "Culture & History",
        "keywords": [
            "culture", "cultural", "history", "historic", "tradition", "traditional",
            "artifact", "artifacts", "explanation", "preserved", "architecture",
        ],
        "poi_categories": ["museum_cultural", "castle_historic"],
    },
]
CATEGORY_PRIORITY = [item["label"] for item in CATEGORY_DEFINITIONS]
CATEGORY_LOOKUP = {item["label"]: item for item in CATEGORY_DEFINITIONS}
CATEGORY_JA_LABELS = {
    "Scenic Spots & Landscapes": "景色・観光地",
    "Temples & Spiritual Heritage": "寺院・精神文化遺産",
    "Castles & Historic Landmarks": "城郭・歴史名所",
    "Dinosaurs & Museums": "恐竜・博物館",
    "Food & Local Cuisine": "グルメ・食文化",
    "Nature & Coast": "自然・海岸",
    "Photography & Seasonal Beauty": "写真・四季の美しさ",
    "Shopping & Local Crafts": "買い物・地域工芸",
    "Access & Visitor Logistics": "アクセス・観光利便性",
    "Culture & History": "文化・歴史",
}
JAPANESE_CATEGORY_DEFINITIONS = [
    {
        "label": "Scenic Spots & Landscapes",
        "keywords": ["景色", "眺め", "絶景", "風景", "きれい", "綺麗", "美しい", "自然", "海", "山", "桜", "紅葉"],
    },
    {
        "label": "Temples & Spiritual Heritage",
        "keywords": ["神社", "寺", "寺院", "仏閣", "参拝", "御朱印", "永平寺", "大仏"],
    },
    {
        "label": "Castles & Historic Landmarks",
        "keywords": ["城", "城跡", "歴史", "史跡", "遺跡", "武家", "資料館", "文化財"],
    },
    {
        "label": "Dinosaurs & Museums",
        "keywords": ["恐竜", "博物館", "美術館", "展示", "化石", "ミュージアム", "資料館"],
    },
    {
        "label": "Food & Local Cuisine",
        "keywords": ["美味しい", "食事", "食べ物", "料理", "飲食", "ランチ", "カフェ", "レストラン", "海鮮", "そば", "蟹", "カニ"],
    },
    {
        "label": "Nature & Coast",
        "keywords": ["自然", "海", "山", "川", "湖", "海岸", "浜", "岬", "東尋坊", "森林"],
    },
    {
        "label": "Photography & Seasonal Beauty",
        "keywords": ["写真", "撮影", "映え", "Instagram", "インスタ", "桜", "紅葉", "雪", "季節"],
    },
    {
        "label": "Shopping & Local Crafts",
        "keywords": ["お土産", "買い物", "売店", "市場", "物産", "工芸", "伝統工芸", "越前", "和紙", "刃物", "漆器"],
    },
    {
        "label": "Access & Visitor Logistics",
        "keywords": ["駅", "新幹線", "電車", "バス", "タクシー", "駐車場", "交通", "アクセス", "移動", "案内", "看板", "地図", "トイレ"],
    },
    {
        "label": "Culture & History",
        "keywords": ["文化", "歴史", "伝統", "祭り", "イベント", "体験", "まちあるき", "街歩き", "芸術", "建物"],
    },
]
JAPANESE_CATEGORY_PRIORITY = [item["label"] for item in JAPANESE_CATEGORY_DEFINITIONS]
JAPANESE_CATEGORY_LOOKUP = {item["label"]: item for item in JAPANESE_CATEGORY_DEFINITIONS}
WORD_JA_LABELS = {
    "beautiful": "美しい",
    "castle": "城",
    "cherry": "桜",
    "crowded": "混雑",
    "dinosaur": "恐竜",
    "echizen": "越前",
    "english": "英語",
    "entrance": "入口",
    "exhibit": "展示",
    "food": "食",
    "friendly": "親切",
    "fukui": "福井",
    "garden": "庭園",
    "ground": "境内",
    "history": "歴史",
    "information": "案内",
    "katsuyama": "勝山",
    "knife": "刃物",
    "large": "大規模",
    "snow": "雪",
    "tsuruga": "敦賀",
    "view": "眺望",
    "winter": "冬",
}

JAPANESE_KEYWORD_TRANSLATIONS = {
    "アクセスが悪": "poor access",
    "交通の便が悪": "poor transport",
    "交通が不便": "inconvenient transport",
    "公共交通": "public transport",
    "バスが少な": "few buses",
    "バスの本数": "bus frequency",
    "電車が少な": "few trains",
    "便が少な": "few services",
    "本数が少な": "few services",
    "乗り継ぎ": "transfers",
    "遠い": "far away",
    "行きにく": "hard to get to",
    "車がない": "no car",
    "車でないと": "need a car",
    "駅から遠": "far from station",
    "移動が大変": "difficult movement",
    "タクシーが少な": "few taxis",
    "タクシーがつかまら": "hard to get taxi",
    "タクシー待ち": "taxi wait",
    "案内がわかりにく": "unclear guidance",
    "案内表示": "signage",
    "表示がわかりにく": "unclear signage",
    "看板": "signs",
    "標識": "signposts",
    "道案内": "directions",
    "道がわかりにく": "confusing route",
    "迷った": "got lost",
    "場所がわかりにく": "hard to find",
    "入口がわかりにく": "unclear entrance",
    "地図": "map",
    "英語": "English",
    "外国語": "foreign languages",
    "多言語": "multilingual",
    "翻訳": "translation",
    "インバウンド": "inbound visitors",
    "外国人向け": "for foreign visitors",
    "外国人対応": "foreign visitor support",
    "接客が悪": "poor service",
    "接客に不満": "service dissatisfaction",
    "対応が悪": "poor response",
    "スタッフの対応": "staff response",
    "店員の対応": "staff response",
    "職員の対応": "staff response",
    "説明不足": "insufficient explanation",
    "不親切": "unhelpful",
    "態度が悪": "poor attitude",
    "案内不足": "insufficient guidance",
    "予約でき": "reservation issue",
    "予約が取れ": "could not reserve",
    "予約が必要": "reservation needed",
    "チケットが買え": "ticket purchase issue",
    "入場券が買え": "ticket purchase issue",
    "売り切れ": "sold out",
    "満席": "fully booked",
    "事前予約": "advance booking",
    "現金のみ": "cash only",
    "キャッシュレス未対応": "no cashless payment",
    "クレジットが使え": "credit card issue",
    "支払いが不便": "payment inconvenience",
    "決済が不便": "payment inconvenience",
    "混雑": "crowding",
    "混んで": "crowded",
    "人が多": "many people",
    "行列": "queue",
    "待ち時間": "wait time",
    "待った": "waited",
    "並ん": "lined up",
    "渋滞": "traffic congestion",
    "駐車場待ち": "parking wait",
    "長蛇": "long line",
    "料金が高": "high fee",
    "値段が高": "high price",
    "価格が高": "high price",
    "割高": "expensive",
    "コスパが悪": "poor value",
    "入場料が高": "high admission",
    "駐車料金が高": "high parking fee",
    "有料なの": "paid service",
    "費用が高": "high cost",
    "汚い": "dirty",
    "不衛生": "unsanitary",
    "清潔でない": "not clean",
    "清潔感がない": "not clean",
    "トイレが汚": "dirty toilets",
    "トイレが少な": "few toilets",
    "臭い": "bad smell",
    "暑すぎ": "too hot",
    "寒すぎ": "too cold",
    "休憩": "rest area",
    "ベンチが少な": "few benches",
    "日陰がない": "no shade",
    "雨宿りでき": "no rain shelter",
    "施設が古": "old facilities",
    "老朽": "aging facilities",
    "休み": "closed",
    "休館": "closed",
    "定休日": "regular closing day",
    "閉まって": "closed",
    "営業時間": "opening hours",
    "時間が短": "short hours",
    "早く閉": "closes early",
    "開いていな": "not open",
    "利用できな": "unavailable",
    "中止": "cancelled",
    "時間が足り": "not enough time",
    "時間がかか": "takes time",
    "見るものが少な": "little to see",
    "何もない": "nothing there",
    "周辺に何も": "nothing nearby",
    "ついでに行きにく": "hard to combine",
    "効率が悪": "inefficient",
    "日程が組みにく": "hard to schedule",
    "予定が立てにく": "hard to plan",
    "回りにく": "hard to tour",
    "階段": "stairs",
    "段差": "steps",
    "坂": "slope",
    "急な坂": "steep slope",
    "急階段": "steep stairs",
    "バリアフリー": "barrier-free access",
    "車椅子": "wheelchair",
    "ベビーカー": "stroller",
    "高齢者": "older visitors",
    "足が悪": "mobility difficulty",
    "歩きにく": "hard to walk",
    "滑り": "slippery",
    "狭い": "narrow",
    "飲食店が少な": "few restaurants",
    "飲食店がない": "no restaurants",
    "食事するところが少な": "few places to eat",
    "食事するところがない": "no places to eat",
    "食べるところが少な": "few places to eat",
    "食べるところがない": "no places to eat",
    "レストランが少な": "few restaurants",
    "レストランがない": "no restaurants",
    "カフェが少な": "few cafes",
    "カフェがない": "no cafes",
    "売店が少な": "few shops",
    "売店がない": "no shops",
    "お土産が少な": "few souvenirs",
    "コンビニがない": "no convenience store",
    "施設が少な": "few facilities",
    "店が少な": "few shops",
    "店舗が少な": "few shops",
}

JAPANESE_TOURISM_KEYWORDS = [
    ("福井", "Fukui"),
    ("石川", "Ishikawa"),
    ("金沢", "Kanazawa"),
    ("駅", "station"),
    ("福井駅", "Fukui Station"),
    ("新幹線", "Shinkansen"),
    ("電車", "train"),
    ("バス", "bus"),
    ("タクシー", "taxi"),
    ("レンタカー", "rental car"),
    ("自家用車", "private car"),
    ("駐車場", "parking"),
    ("交通", "transport"),
    ("公共交通", "public transport"),
    ("アクセス", "access"),
    ("移動", "mobility"),
    ("観光", "tourism"),
    ("旅行", "travel"),
    ("宿泊", "lodging"),
    ("ホテル", "hotel"),
    ("温泉", "hot springs"),
    ("飲食店", "restaurants"),
    ("レストラン", "restaurant"),
    ("カフェ", "cafe"),
    ("ランチ", "lunch"),
    ("食事", "meal"),
    ("食べ物", "food"),
    ("美味しい", "delicious"),
    ("お土産", "souvenirs"),
    ("買い物", "shopping"),
    ("市場", "market"),
    ("イベント", "events"),
    ("祭り", "festival"),
    ("自然", "nature"),
    ("海", "sea"),
    ("山", "mountains"),
    ("景色", "scenery"),
    ("桜", "cherry blossoms"),
    ("紅葉", "autumn leaves"),
    ("恐竜", "dinosaurs"),
    ("博物館", "museum"),
    ("美術館", "art museum"),
    ("歴史", "history"),
    ("文化", "culture"),
    ("神社", "shrine"),
    ("寺", "temple"),
    ("城", "castle"),
    ("まちあるき", "city walking"),
    ("体験", "activities"),
    ("施設", "facilities"),
    ("トイレ", "toilets"),
    ("案内", "guidance"),
    ("看板", "signs"),
    ("地図", "map"),
    ("英語", "English"),
    ("外国語", "foreign languages"),
    ("多言語", "multilingual"),
    ("情報", "information"),
    ("Instagram", "Instagram"),
    ("インターネット", "internet"),
    ("観光協会", "tourism association"),
    ("パンフレット", "brochure"),
]


def load_review_dataset(
    input_csv: Path,
    city: str | None = "Fukui",
    source_platform: str = "google_places",
) -> pd.DataFrame:
    df = pd.read_csv(input_csv)
    if "review_text" not in df.columns:
        raise ValueError(f"Expected a 'review_text' column in {input_csv}")
    if source_platform and "source_platform" in df.columns:
        df = df[df["source_platform"].fillna("").eq(source_platform)]
    if city:
        df = df[df["city"].fillna("").str.casefold() == city.casefold()]
    df = df[df["review_text"].fillna("").str.strip().ne("")].copy()
    return df.reset_index(drop=True)


def _is_useful_term(term: str) -> bool:
    if not term or any(pat.match(term) for pat in LOW_SIGNAL_PATTERNS):
        return False
    tokens = term.split()
    if not tokens:
        return False
    if all(token in KEYWORD_STOPWORDS for token in tokens):
        return False
    if len(tokens) == 1 and (len(tokens[0]) < 4 or tokens[0] in GENERIC_SINGLE_TERMS):
        return False
    if term.count("'") > 1:
        return False
    return True


def _normalize_text_series(texts: pd.Series) -> pd.Series:
    cleaned = (
        texts.fillna("")
        .astype(str)
        .str.lower()
        .str.replace(r"[\r\n\t]+", " ", regex=True)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )
    return cleaned[cleaned.ne("")]


def _canonicalize_term(term: str) -> str:
    return CANONICAL_TERM_MAP.get(term, term)


def _count_keyword_hits(text: str, keywords: list[str]) -> int:
    hits = 0
    for keyword in keywords:
        if re.search(r"\b" + re.escape(keyword) + r"\b", text):
            hits += 1
    return hits


def classify_review_category(review_text: str, poi_category: str = "") -> str | None:
    if not isinstance(review_text, str) or not review_text.strip():
        return None

    text = review_text.lower()
    poi_category = (poi_category or "").strip().lower()

    best_label = None
    best_score = 0.0
    for label in CATEGORY_PRIORITY:
        definition = CATEGORY_LOOKUP[label]
        score = float(_count_keyword_hits(text, definition["keywords"]))
        if poi_category and poi_category in definition["poi_categories"]:
            score += 0.75
        if score > best_score:
            best_label = label
            best_score = score

    if best_score <= 0:
        return None
    return best_label


def summarize_topic_categories(reviews_df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    working = reviews_df.copy()
    if "poi_category" not in working.columns:
        working["poi_category"] = ""
    working["topic_category"] = working.apply(
        lambda row: classify_review_category(row.get("review_text", ""), row.get("poi_category", "")),
        axis=1,
    )
    working = working[working["topic_category"].notna()].copy()

    if working.empty:
        return pd.DataFrame(columns=["rank", "term", "count", "percentage"])

    counts = (
        working["topic_category"]
        .value_counts()
        .rename_axis("term")
        .reset_index(name="count")
        .head(top_n)
    )
    total = float(counts["count"].sum())
    counts["rank"] = np.arange(1, len(counts) + 1)
    counts["percentage"] = np.where(total > 0, counts["count"] / total * 100, 0.0)
    return counts[["rank", "term", "count", "percentage"]]


def classify_japanese_topic_category(text: str) -> str | None:
    if not isinstance(text, str) or not text.strip():
        return None

    best_label = None
    best_score = 0
    for label in JAPANESE_CATEGORY_PRIORITY:
        definition = JAPANESE_CATEGORY_LOOKUP[label]
        score = sum(1 for keyword in definition["keywords"] if keyword in text)
        if score > best_score:
            best_label = label
            best_score = score

    if best_score <= 0:
        return None
    return best_label


def summarize_japanese_topic_categories(texts: pd.Series, top_n: int = 10) -> pd.DataFrame:
    clean_texts = texts.fillna("").astype(str).str.strip()
    clean_texts = clean_texts[clean_texts.ne("")]
    if clean_texts.empty:
        return pd.DataFrame(columns=["rank", "term", "count", "percentage"])

    categories = clean_texts.map(classify_japanese_topic_category).dropna()
    if categories.empty:
        return pd.DataFrame(columns=["rank", "term", "count", "percentage"])

    counts = categories.value_counts().rename_axis("term").reset_index(name="count").head(top_n)
    total = float(counts["count"].sum())
    counts["rank"] = np.arange(1, len(counts) + 1)
    counts["percentage"] = np.where(total > 0, counts["count"] / total * 100, 0.0)
    return counts[["rank", "term", "count", "percentage"]]


def extract_keyword_frequencies(reviews_df: pd.DataFrame, top_k: int = 40, min_frequency: int = 2) -> pd.DataFrame:
    texts = _normalize_text_series(reviews_df["review_text"])
    if texts.empty:
        return pd.DataFrame(columns=["term", "count"])

    vectorizer = CountVectorizer(
        lowercase=True,
        stop_words=list(KEYWORD_STOPWORDS),
        ngram_range=(1, 2),
        token_pattern=TOKEN_RE.pattern,
    )
    matrix = vectorizer.fit_transform(texts.tolist())
    counts = np.asarray(matrix.sum(axis=0)).ravel()
    terms = np.array(vectorizer.get_feature_names_out())

    keyword_df = (
        pd.DataFrame({"term": terms, "count": counts})
        .assign(term=lambda df: df["term"].map(_canonicalize_term))
        .query("term != ''")
        .groupby("term", as_index=False, sort=False)["count"].sum()
        .query("count >= @min_frequency")
        .sort_values(["count", "term"], ascending=[False, True])
        .reset_index(drop=True)
    )
    keyword_df = keyword_df[keyword_df["term"].map(_is_useful_term)].copy()
    if keyword_df.empty:
        return keyword_df

    selected = []
    selected_terms: list[str] = []
    for row in keyword_df.itertuples(index=False):
        tokens = set(row.term.split())
        if any(tokens < set(existing.split()) for existing in selected_terms):
            continue
        selected.append({"term": row.term, "count": int(row.count)})
        selected_terms.append(row.term)
        if len(selected) >= top_k:
            break
    return pd.DataFrame(selected)


def extract_japanese_tourism_keyword_frequencies(
    texts: pd.Series,
    top_k: int = 40,
    min_frequency: int = 2,
) -> pd.DataFrame:
    clean_texts = texts.fillna("").astype(str).str.strip()
    clean_texts = clean_texts[clean_texts.ne("")]
    rows = []
    for term, translation in JAPANESE_TOURISM_KEYWORDS:
        count = int(clean_texts.str.contains(term, regex=False, na=False).sum())
        if count >= min_frequency:
            display = term if term.isascii() else f"{term} ({translation})"
            rows.append(
                {
                    "term": term,
                    "display": display,
                    "translation": "" if term.isascii() else translation,
                    "count": count,
                }
            )
    if not rows:
        return pd.DataFrame(columns=["rank", "term", "display", "translation", "count", "percentage"])

    df = pd.DataFrame(rows).sort_values(["count", "term"], ascending=[False, True]).head(top_k).reset_index(drop=True)
    total = float(df["count"].sum())
    df["rank"] = np.arange(1, len(df) + 1)
    df["percentage"] = np.where(total > 0, df["count"] / total * 100, 0.0)
    return df[["rank", "term", "display", "translation", "count", "percentage"]]


def _display_term(term: str) -> str:
    base = term.title()
    ja = WORD_JA_LABELS.get(term.lower())
    if ja:
        return f"{base} {ja}"
    return base


def _display_cloud_term(term: str, translation: str | None = None, japanese_first: bool = False) -> str:
    if japanese_first:
        gloss = translation or JAPANESE_KEYWORD_TRANSLATIONS.get(term, "")
        return f"{term}\n({gloss})" if gloss else term
    return _display_term(term)


def _display_category_label(term: str) -> str:
    ja = CATEGORY_JA_LABELS.get(term)
    if not ja:
        return term
    return f"{term}（{ja}）"


def _draw_table(ax: plt.Axes, ranked_df: pd.DataFrame, report_title: str) -> None:
    ax.axis("off")
    ax.text(
        0.5, 1.07, report_title, transform=ax.transAxes, ha="center", va="bottom",
        fontsize=17, color="white", fontweight="bold",
        bbox={"boxstyle": "round,pad=0.55", "facecolor": "#FF2D2D", "edgecolor": "#FF2D2D"},
    )

    if ranked_df.empty:
        ax.text(0.5, 0.5, "No topic categories available", ha="center", va="center", fontsize=14)
        return

    ax.set_xlim(0, 1)
    ax.set_ylim(0, len(ranked_df) + 1.4)
    header_y = len(ranked_df) + 0.65
    row_height = 0.9
    col_edges = [0.0, 0.09, 0.72, 0.86, 1.0]

    ax.add_patch(
        patches.FancyBboxPatch(
            (0.0, header_y - 0.45), 1.0, 0.75,
            boxstyle="round,pad=0.01,rounding_size=0.02",
            facecolor="#FF4B4B", edgecolor="#FF4B4B",
        )
    )

    term_header = ranked_df.attrs.get("term_header", "Topic Category（トピックカテゴリ）")
    for idx, label in enumerate(["Rank", term_header, "Percentage（割合）", ""]):
        x = (col_edges[idx] + col_edges[idx + 1]) / 2
        ax.text(x, header_y - 0.06, label, color="white", fontsize=13, fontweight="bold",
                ha="center", va="center")

    max_pct = ranked_df["percentage"].max()
    for row in ranked_df.itertuples(index=False):
        y = len(ranked_df) - row.rank + 0.5
        ax.add_patch(
            patches.Rectangle((0.0, y - row_height / 2), 1.0, row_height,
                              facecolor="white", edgecolor="#E8EAED", linewidth=0.8)
        )

        ax.scatter([0.045], [y], s=400, c="#FF2D2D", zorder=3, linewidths=0)
        ax.text(0.045, y, str(row.rank), ha="center", va="center",
                fontsize=11, color="white", fontweight="bold", zorder=4)
        category_label = getattr(row, "display", None) or _display_category_label(str(row.term))
        category_fontsize = 12.0 if len(category_label) <= 34 else 11.0
        ax.text(0.10, y, category_label, ha="left", va="center",
                fontsize=category_fontsize, color="#111827")
        ax.text(0.795, y, f"{row.percentage:.1f}%", ha="center", va="center",
                fontsize=13, color="#111827", fontweight="bold")

        bar_x = 0.875
        bar_w = 0.10
        ax.add_patch(
            patches.Rectangle(
                (bar_x, y - 0.13), bar_w, 0.26,
                facecolor="#FFE0E0", edgecolor="none",
            )
        )
        fill_w = 0 if max_pct == 0 else bar_w * (row.percentage / max_pct)
        if fill_w > 0:
            ax.add_patch(
                patches.Rectangle(
                    (bar_x, y - 0.13), fill_w, 0.26,
                    facecolor="#FF3B3B", edgecolor="none",
                )
            )


def _try_place_words(ax: plt.Axes, cloud_df: pd.DataFrame, seed: int, japanese_first: bool = False) -> None:
    rng = random.Random(seed)
    renderer = ax.figure.canvas.get_renderer()
    placed_boxes = []
    ax_bbox = ax.get_window_extent(renderer=renderer)
    max_count = float(cloud_df["count"].max())
    min_count = float(cloud_df["count"].min())

    n = len(cloud_df)
    for idx, row in enumerate(cloud_df.itertuples(index=False)):
        if japanese_first:
            label = _display_cloud_term(
                str(row.term),
                translation=getattr(row, "translation", None),
                japanese_first=True,
            )
        else:
            label = getattr(row, "display", None) or _display_term(str(row.term))
        t = 0.0 if math.isclose(max_count, min_count) else (row.count - min_count) / (max_count - min_count)
        font_size = 12 + t * 17 if japanese_first else 15 + t * 20
        color = PALETTE[idx % len(PALETTE)]
        fontweight = "bold" if idx < 6 else "semibold"
        placed = False

        # Phase 1: preferred zone — tight for high-frequency, expands for low-frequency
        p1_sx = 0.13 + 0.15 * (1.0 - t)
        p1_sy = 0.10 + 0.12 * (1.0 - t)
        # Phase 2: full-canvas wide search for words that couldn't fit in preferred zone
        phases = [
            (350, 0.50, p1_sx, 0.50, p1_sy),
            (250, 0.50, 0.28, 0.50, 0.23),
        ]

        for max_tries, cx, sx, cy, sy in phases:
            if placed:
                break
            for _ in range(max_tries):
                x = min(max(rng.gauss(cx, sx), 0.07), 0.93)
                y = min(max(rng.gauss(cy, sy), 0.07), 0.93)
                text = ax.text(
                    x, y, label, ha="center", va="center", fontsize=font_size, color=color,
                    fontweight=fontweight, transform=ax.transAxes, linespacing=0.84,
                )
                ax.figure.canvas.draw()
                bbox = text.get_window_extent(renderer=renderer).expanded(1.04, 1.12)
                within = (
                    bbox.x0 >= ax_bbox.x0 + 4 and bbox.y0 >= ax_bbox.y0 + 4
                    and bbox.x1 <= ax_bbox.x1 - 4 and bbox.y1 <= ax_bbox.y1 - 4
                )
                overlaps = any(bbox.overlaps(existing) for existing in placed_boxes)
                if within and not overlaps:
                    placed_boxes.append(bbox)
                    placed = True
                    break
                text.remove()

        if not placed:
            # Circular fallback: spread evenly around center instead of corner grid
            angle = (idx / max(n, 1)) * 2 * math.pi
            fx = min(max(0.50 + 0.36 * math.cos(angle), 0.08), 0.92)
            fy = min(max(0.50 + 0.28 * math.sin(angle), 0.08), 0.92)
            text = ax.text(
                fx, fy, label, ha="center", va="center",
                fontsize=max(11, font_size - 3), color=color,
                fontweight=fontweight, transform=ax.transAxes, linespacing=0.84,
            )
            ax.figure.canvas.draw()
            placed_boxes.append(text.get_window_extent(renderer=renderer).expanded(1.02, 1.08))


def render_keyword_cloud_report(
    ranked_df: pd.DataFrame,
    cloud_df: pd.DataFrame,
    output_path: Path,
    title: str,
    subtitle: str,
    review_count: int,
    seed: int = 7,
    japanese_first: bool = False,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(9.2, 12.8), facecolor="white")
    gs = fig.add_gridspec(100, 1, hspace=0)
    table_ax = fig.add_subplot(gs[7:46, 0])
    cloud_ax = fig.add_subplot(gs[57:97, 0])

    _draw_table(table_ax, ranked_df, title)

    cloud_ax.axis("off")
    cloud_ax.set_facecolor("white")
    cloud_ax.text(
        0.5, 1.06, subtitle, transform=cloud_ax.transAxes, ha="center", va="bottom",
        fontsize=15, color="white", fontweight="bold",
        bbox={"boxstyle": "round,pad=0.50", "facecolor": "#FF2D2D", "edgecolor": "#FF2D2D"},
    )

    fig.canvas.draw()
    if not cloud_df.empty:
        _try_place_words(cloud_ax, cloud_df, seed=seed, japanese_first=japanese_first)

    plt.tight_layout(rect=(0.04, 0.02, 0.96, 0.96))
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return output_path


def load_codebook_yaml(path: Path) -> dict:
    with open(path) as f:
        raw = yaml.safe_load(f)
    return {
        code: {
            "label": attrs["label"],
            "type": attrs["type"],
            "keywords": [str(keyword) for keyword in attrs.get("keywords", [])],
        }
        for code, attrs in raw.get("friction_codes", {}).items()
    }


def _english_keyword_doc_mask(texts: pd.Series, keyword: str) -> pd.Series:
    keyword = keyword.lower().strip()
    if not keyword:
        return pd.Series(False, index=texts.index)
    if "&&" in keyword:
        mask = pd.Series(True, index=texts.index)
        for part in [p.strip() for p in keyword.split("&&") if p.strip()]:
            mask &= _english_keyword_doc_mask(texts, part)
        return mask
    pattern = r"\b" + re.escape(keyword) + r"\b"
    return texts.str.contains(pattern, case=False, regex=True, na=False)


def _japanese_keyword_doc_mask(texts: pd.Series, keyword: str) -> pd.Series:
    keyword = keyword.strip()
    if not keyword:
        return pd.Series(False, index=texts.index)
    return texts.str.contains(keyword, regex=False, na=False)


def extract_codebook_keyword_frequencies(
    texts: pd.Series,
    codebook: dict,
    *,
    language: str,
    top_k: int = 24,
    min_frequency: int = 2,
) -> pd.DataFrame:
    clean_texts = texts.fillna("").astype(str).str.strip()
    clean_texts = clean_texts[clean_texts.ne("")]
    rows = []
    for code, attrs in codebook.items():
        if attrs.get("type") != "friction":
            continue
        for keyword in attrs.get("keywords", []):
            if not keyword:
                continue
            if language == "ja":
                mask = _japanese_keyword_doc_mask(clean_texts, keyword)
                display = f"{keyword} ({JAPANESE_KEYWORD_TRANSLATIONS.get(keyword, attrs['label'])})"
                translation = JAPANESE_KEYWORD_TRANSLATIONS.get(keyword, attrs["label"])
            else:
                mask = _english_keyword_doc_mask(clean_texts.str.lower(), keyword)
                display = keyword.replace("&&", "+").title()
                translation = None
            count = int(mask.sum())
            if count >= min_frequency:
                rows.append(
                    {
                        "term": keyword,
                        "display": display,
                        "translation": translation,
                        "friction_code": code,
                        "friction_label": attrs["label"],
                        "count": count,
                    }
                )
    if not rows:
        return pd.DataFrame(columns=["rank", "term", "display", "translation", "friction_code", "friction_label", "count", "percentage"])

    df = pd.DataFrame(rows).sort_values(["count", "term"], ascending=[False, True]).head(top_k).reset_index(drop=True)
    total = float(df["count"].sum())
    df["rank"] = np.arange(1, len(df) + 1)
    df["percentage"] = np.where(total > 0, df["count"] / total * 100, 0.0)
    return df[["rank", "term", "display", "translation", "friction_code", "friction_label", "count", "percentage"]]


def generate_codebook_keyword_cloud_report(
    input_csv: Path,
    codebook_path: Path,
    output_path: Path,
    *,
    text_col: str,
    title: str,
    subtitle: str,
    city: str | None = None,
    source_platform: str | None = None,
    prefecture: str | None = None,
    language: str = "en",
    top_n: int = 10,
    cloud_terms: int = 18,
    min_frequency: int = 2,
    seed: int = 7,
) -> tuple[pd.DataFrame, Path]:
    df = pd.read_csv(input_csv, low_memory=False)
    if text_col not in df.columns:
        raise ValueError(f"Expected a '{text_col}' column in {input_csv}")
    if city and "city" in df.columns:
        df = df[df["city"].fillna("").str.casefold() == city.casefold()]
    if source_platform and "source_platform" in df.columns:
        df = df[df["source_platform"].fillna("").eq(source_platform)]
    if prefecture and "survey_prefecture" in df.columns:
        df = df[df["survey_prefecture"].fillna("").str.casefold() == prefecture.casefold()]

    codebook = load_codebook_yaml(codebook_path)
    ranked_df = extract_codebook_keyword_frequencies(
        df[text_col],
        codebook,
        language=language,
        top_k=max(top_n, cloud_terms),
        min_frequency=min_frequency,
    )
    table_df = ranked_df.head(top_n).copy()
    table_df["rank"] = np.arange(1, len(table_df) + 1)
    table_df.attrs["term_header"] = "Keyword（キーワード）"
    cloud_df = ranked_df.head(cloud_terms)
    report_path = render_keyword_cloud_report(
        ranked_df=table_df,
        cloud_df=cloud_df,
        output_path=output_path,
        title=title,
        subtitle=subtitle,
        review_count=len(df),
        seed=seed,
        japanese_first=language == "ja",
    )
    return table_df, report_path


def generate_japanese_tourism_keyword_cloud_report(
    input_csv: Path,
    output_path: Path,
    *,
    text_cols: list[str],
    title: str,
    subtitle: str,
    prefecture: str | None = None,
    top_n: int = 10,
    cloud_terms: int = 18,
    min_frequency: int = 2,
    seed: int = 7,
) -> tuple[pd.DataFrame, Path]:
    df = pd.read_csv(input_csv, low_memory=False)
    if prefecture and "survey_prefecture" in df.columns:
        df = df[df["survey_prefecture"].fillna("").str.casefold() == prefecture.casefold()]

    available_cols = [col for col in text_cols if col in df.columns]
    if not available_cols:
        raise ValueError(f"None of the requested text columns exist in {input_csv}: {text_cols}")

    combined = (
        df[available_cols]
        .fillna("")
        .astype(str)
        .agg("。".join, axis=1)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )
    ranked_df = extract_japanese_tourism_keyword_frequencies(
        combined,
        top_k=max(top_n, cloud_terms),
        min_frequency=min_frequency,
    )
    table_df = summarize_japanese_topic_categories(combined, top_n=top_n)
    cloud_df = ranked_df.head(cloud_terms)
    report_path = render_keyword_cloud_report(
        ranked_df=table_df,
        cloud_df=cloud_df,
        output_path=output_path,
        title=title,
        subtitle=subtitle,
        review_count=len(df),
        seed=seed,
        japanese_first=True,
    )
    return table_df, report_path


def generate_keyword_cloud_report(
    input_csv: Path,
    output_path: Path,
    city: str | None = "Fukui",
    source_platform: str = "google_places",
    top_n: int = 10,
    cloud_terms: int = 24,
    min_frequency: int = 2,
    seed: int = 7,
) -> tuple[pd.DataFrame, Path]:
    reviews_df = load_review_dataset(input_csv, city=city, source_platform=source_platform)
    ranked_df = summarize_topic_categories(reviews_df, top_n=top_n)
    keyword_df = extract_keyword_frequencies(
        reviews_df,
        top_k=max(top_n, cloud_terms),
        min_frequency=min_frequency,
    )
    cloud_df = keyword_df.head(cloud_terms)

    title = "GOOGLE PLACES（グーグルプレイス）"
    report_path = render_keyword_cloud_report(
        ranked_df=ranked_df,
        cloud_df=cloud_df,
        output_path=output_path,
        title=title,
        subtitle="WORD CLOUD（ワードクラウド）",
        review_count=len(reviews_df),
        seed=seed,
    )
    return ranked_df, report_path
