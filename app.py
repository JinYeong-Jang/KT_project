# -*- coding: utf-8 -*-
# app.py
# -----------------------------------------------------------------------------
# 집회/시위 알림 서비스 (Streamlit)
# - 월간 달력 + 일자별 상세 (집회정보/버스우회/관련기사/피드백/워드클라우드)
# - 간단 챗봇(텍스트 지식 기반) — 플로팅 버튼(FAB)로 모달 열림
# - 디자인/레이아웃 통일, 뉴스 카드형 링크, 버스표 컬럼 정리
# -----------------------------------------------------------------------------

# ====================== 0) 기본 임포트 & 환경 설정 ============================
import os
import re
import textwrap
import base64
from io import BytesIO
from pathlib import Path
from datetime import date, datetime
from collections import Counter
from urllib.parse import urlparse
import html

import pandas as pd
import streamlit as st
import pydeck as pdk
from dateutil import parser
from streamlit_calendar import calendar

# Chatbot deps
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate

# Wordcloud (선택)
try:
    from wordcloud import WordCloud
    WORDCLOUD_AVAILABLE = True
except Exception:
    WORDCLOUD_AVAILABLE = False

# .env 로드 & 필수 키 체크
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise ValueError("❌ OPENAI_API_KEY 환경변수가 설정되지 않았습니다. .env 파일을 확인하세요.")

# Streamlit 페이지 설정
st.set_page_config(page_title="집회/시위 알림 서비스", page_icon="📅", layout="wide")


# ====================== 1) 공통 스타일/CSS & 헤더 =============================
def get_base64_of_image(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

logo_base64 = get_base64_of_image("data/assets/logo.png")

# 헤더 로고
st.markdown(
    f"""
    <div style='display:flex; justify-content:left; align-items:left; padding:10px;'>
      <img src="data:image/png;base64,{logo_base64}" alt="Logo" style="height:60px;">
    </div>
    """,
    unsafe_allow_html=True,
)

# 전역 CSS (타이포/카드/버튼/캘린더/뉴스카드/여백 + FAB/모달)
st.markdown(
    """
<style>
/* 전체 배경 */
.stApp, .main, [data-testid="stHeader"] { background:#ffffff !important; }

/* 상단 타이틀 박스 */
.app-header{
  border:1px solid #e5e7eb; border-radius:12px;
  background:#f3f4f6; padding:14px 24px;
  font-weight:800; font-size:20px; color:#111827;
  text-align:center; margin:6px 0 16px 0;
}

/* 카드 공통 */
.card { border:1px solid #e5e7eb; border-radius:14px; padding:16px; margin:12px 6px; background:#fff; }
.time { font-weight:800; font-size:18px; margin-bottom:6px; color:#111827; }
.sub  { color:#6b7280; font-size:14px; margin-bottom:8px; }
.meta { color:#374151; font-size:14px; }
a.card-link { display:block; text-decoration:none; color:inherit; }
a.card-link .card:hover { border-color:#94a3b8; background:#f8fafc; }

/* FullCalendar: 도트/버튼 (페이지 전역, iframe 밖) */
.fc .fc-daygrid-dot-event .fc-event-time,
.fc .fc-daygrid-dot-event .fc-event-title,
.fc .fc-daygrid-event-harness .fc-event-time,
.fc .fc-daygrid-event-harness .fc-event-title { display:none !important; }
.fc-daygrid-dot-event > .fc-event-dot { width:10px; height:10px; border:0; }

/* prev/next 커스텀 아이콘 */
.fc .fc-prev-button .fc-icon, .fc .fc-next-button .fc-icon { display:none !important; }
.fc .fc-prev-button:before { content:"◀"; font-size:22px; color:#000; }
.fc .fc-next-button:before { content:"▶"; font-size:22px; color:#000; }
.fc-daygrid-more-link { font-size:12px; color:#000; }
.fc-daygrid-more-link::after { content:""; }

/* ====== 뉴스 카드 ====== */
.news-wrap { margin:0; }
.news-grid { display:flex; flex-direction:column; gap:12px; }
.news-card { display:flex; flex-direction:column; gap:6px; padding:14px 16px; border:1px solid #e5e7eb; border-radius:12px; background:#fff; }
.news-title { font-size:16px; font-weight:700; color:#111827; line-height:1.35; }
.news-meta  { font-size:13px; color:#6b7280; }
.news-link  { display:inline-block; margin-left:8px; padding:5px 10px; border-radius:10px; background:#eef2ff; border:1px solid #c7d2fe; text-decoration:none; font-weight:600; color:#1f2937; }
.news-link:hover { background:#e0e7ff; }

/* 섹션 간격 유틸 */
.gap-16 { height:16px; }
.gap-24 { height:24px; }

/* ====== 채팅 벌룬/입력 ====== */
.chat-wrap { margin-top:4px; }
.chat-scroll{ height:240px; overflow-y:auto; padding:10px 12px; background:#ffffff; }
.msg-row{ display:flex; margin:8px 0; }
.msg-row.user{ justify-content:flex-end; }
.bubble{ max-width:520px; padding:10px 14px; border-radius:14px; font-size:16px; line-height:1.5; word-break:break-word; white-space:pre-wrap; }
.bubble.user{ background:#2A52BF; color:#fff; }
.bubble.bot { background:#eeeeee; color:#000; }

.chat-input-area { padding:8px 0 0 0; }
div[data-baseweb="input"] > div {
  background:#fff !important; border:1px solid #000 !important; border-radius:100px !important;
  padding:8px 14px !important; color:#000; font-size:15px;
}
div.stButton > button{
  background-color: var(--blue); color:#000; border-radius:100px; border:1px solid #000;
  font-weight:600; font-size:15px;
}
div.stButton > button:hover{ background-color:#1d3e91; border:1px solid #1d3e91; color:#fff; }

/* ====== FAB ====== */
.fab-chat {
  position: fixed; right: 24px; bottom: 24px;
  width: 56px; height: 56px; border-radius: 50%;
  display:flex; align-items:center; justify-content:center;
  background:#2A52BF; color:#fff; text-decoration:none;
  font-size:24px; font-weight:700; box-shadow:0 8px 20px rgba(0,0,0,.15);
  z-index: 9998; border:1px solid rgba(0,0,0,.08);
}
.fab-chat:hover { filter: brightness(1.05); }
</style>
""",
    unsafe_allow_html=True,
)

# ====================== 2) 데이터 로드 함수 ================================
def _file_bytes_and_mtime(path: str) -> tuple[bytes, float, Path]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {path}")
    return p.read_bytes(), p.stat().st_mtime, p

@st.cache_data
def load_events(path: str, _mtime: float) -> pd.DataFrame:
    """집회 데이터 로드 + 표준화 컬럼 생성 (파일 mtime으로 캐시 무효화)"""
    data, _, p = _file_bytes_and_mtime(path)
    if p.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(BytesIO(data))
    else:
        df = pd.read_csv(BytesIO(data), encoding="utf-8")
    variants = {
        "date": ["date", "날짜"],
        "start_time": ["start_time", "start", "시작", "starttime"],
        "end_time": ["end_time", "end", "종료", "endtime"],
        "location": ["location", "장소", "place"],
        "district": ["district", "관할서", "구"],
        "reported_head": ["reported_head", "reported_headcount", "신고인원", "인원"],
        "memo": ["memo", "비고", "메모"],
        "link": ["link", "news_link", "기사링크"],
        "title": ["title", "news_title", "기사제목"],
    }
    def find_col(k):
        for cand in variants[k]:
            for c in df.columns:
                if str(c).strip().lower() == cand.lower():
                    return c
        return None
    col = {k: find_col(k) for k in variants}
    for k in ["date", "start_time", "end_time", "location"]:
        if col[k] is None:
            raise ValueError(f"'{k}' 컬럼이 필요합니다.")
    def to_date(x):
        if pd.isna(x):
            return None
        s = str(x).strip()
        if re.match(r"^\d{4}\.\d{1,2}\.\d{1,2}$", s):
            s = s.replace(".", "-")
        try:
            return parser.parse(s).date()
        except Exception:
            return None
    def to_time(x):
        if pd.isna(x):
            return None
        try:
            t = parser.parse(str(x)).time()
            return f"{t.hour:02d}:{t.minute:02d}"
        except Exception:
            return None
    df["_date"] = df[col["date"]].apply(to_date)
    df["_start"] = df[col["start_time"]].apply(to_time)
    df["_end"]   = df[col["end_time"]].apply(to_time)
    df["_loc"]   = df[col["location"]].astype(str)
    df["_dist"]  = df[col["district"]].astype(str) if col["district"] else ""
    df["_head"]  = df[col["reported_head"]] if col["reported_head"] else ""
    df["_memo"]  = df[col["memo"]].astype(str) if col["memo"] else ""
    df["__link"]  = df[col["link"]] if col["link"] else ""
    df["__title"] = df[col["title"]] if col["title"] else ""
    df = df[df["_date"].notnull() & df["_start"].notnull() & df["_end"].notnull()]
    return df.reset_index(drop=True)

@st.cache_data
def load_bus(path: str, _mtime: float) -> pd.DataFrame:
    """버스 우회 데이터 로드 (파일 mtime으로 캐시 무효화)"""
    p = Path(path)
    if not p.exists():
        return pd.DataFrame()
    data = p.read_bytes()
    df = pd.read_excel(BytesIO(data))
    def to_date(x):
        if pd.isna(x):
            return None
        s = str(x).strip()
        if re.match(r"^\d{4}\.\d{1,2}\.\d{1,2}$", s):
            s = s.replace(".", "-")
        try:
            return parser.parse(s).date()
        except Exception:
            return None
    def to_time(x):
        if pd.isna(x):
            return None
        try:
            t = parser.parse(str(x)).time()
            return f"{t.hour:02d}:{t.minute:02d}"
        except Exception:
            return None
    cols = {c: str(c).strip().lower() for c in df.columns}
    def pick(*names):
        for n in names:
            for c, lc in cols.items():
                if lc == n:
                    return c
        return None
    c_sd = pick("start_date", "시작일")
    c_st = pick("start_time", "시작시간")
    c_ed = pick("end_date", "종료일")
    c_et = pick("end_time", "종료시간")
    c_ars = pick("ars_id", "ars", "정류장id")
    c_nm = pick("정류소명", "정류장명", "stop_name")
    c_x  = pick("x좌표", "x", "lon", "lng")
    c_y  = pick("y좌표", "y", "lat")
    if any(c is None for c in [c_sd, c_st, c_ed, c_et, c_ars, c_nm, c_x, c_y]):
        return pd.DataFrame()
    ars_series = (
        df[c_ars].astype(str).map(lambda s: re.sub(r"\D", "", s)).map(lambda s: s.zfill(5))
    )
    out = pd.DataFrame(
        {
            "start_date": df[c_sd].apply(to_date),
            "start_time": df[c_st].apply(to_time),
            "end_date":   df[c_ed].apply(to_date),
            "end_time":   df[c_et].apply(to_time),
            "ARS_ID": ars_series,
            "정류소명": df[c_nm].astype(str),
            "lon": pd.to_numeric(df[c_x], errors="coerce"),
            "lat": pd.to_numeric(df[c_y], errors="coerce"),
        }
    )
    return out.dropna(subset=["start_date", "end_date", "lon", "lat"]).reset_index(drop=True)

@st.cache_data
def load_routes(path: str, _mtime: float) -> pd.DataFrame:
    """노선-정류장 매핑 CSV 로드 (파일 mtime으로 캐시 무효화)"""
    p = Path(path)
    if not p.exists():
        return pd.DataFrame(columns=["date", "ars_id", "route"])
    data = p.read_bytes()
    df = pd.read_csv(BytesIO(data), dtype={"ars_id": str, "route": str})
    def to_date(x):
        try:
            return parser.parse(str(x)).date()
        except Exception:
            return None
    df["date"] = df["date"].apply(to_date)
    df["ars_id"] = df["ars_id"].astype(str).str.replace(r"\D", "", regex=True).str.zfill(5)
    df["route"] = df["route"].fillna("").astype(str).str.strip()
    return df.dropna(subset=["date", "ars_id"]).reset_index(drop=True)


# ====================== 3) 공용 유틸 (캘린더/색상/토크나이즈/워드클라우드) =======
def color_by_headcount(h):
    try:
        n = int(h)
        if n >= 1000:
            return "#ef4444"
        if n >= 500:
            return "#f59e0b"
        return "#3b82f6"
    except Exception:
        return "#3b82f6"

def df_to_month_dots(df: pd.DataFrame):
    """FullCalendar용 월간 도트 이벤트 (+ 클릭 식별용 extendedProps 포함)"""
    events = []
    for _, r in df.iterrows():
        d_iso = str(r["_date"])
        st_iso = f"{r['_date']}T{r['_start']}:00"
        ed_iso = f"{r['_date']}T{r['_end']}:00"
        events.append(
            {
                "title": "",
                "start": st_iso,
                "end": ed_iso,
                "display": "list-item",
                "color": color_by_headcount(r["_head"]),
                "extendedProps": {
                    "d": d_iso,
                    "st": r["_start"],
                    "ed": r["_end"],
                    "loc": r["_loc"],
                },
            }
        )
    return events

def filter_by_day(df: pd.DataFrame, d: date) -> pd.DataFrame:
    return df[df["_date"] == d].sort_values(by=["_start", "_end", "_loc"])

def get_bus_rows_for_date(bus_df: pd.DataFrame, d: date) -> pd.DataFrame:
    if bus_df is None or bus_df.empty:
        return pd.DataFrame()
    return bus_df[(bus_df["start_date"] <= d) & (bus_df["end_date"] >= d)].copy()

# --- 워드클라우드 전처리 ---
_STOPWORDS = {
    "그리고","그러나","하지만","또는","및","때문","때문에","대한","관련","대해",
    "여러분","정도","부분","등","좀","너무","수","것","거","이것","저것","우리",
    "입니다","합니다","하는","있는","되는","됩니다","드립니다","해주시면","해주십시오",
    "해주세요","부탁드립니다","같습니다","감사합니다","감사하겠습니다","불편합니다",
    "입니다만","않습니다","않아요","않구요","됩니다만",
    "으로","로","에서","에게","에는","에","의","을","를","이","가","와","과","도","만","보다",
}
_SUFFIX_PAT = re.compile(
    r"(입니다|합니다|십시오|해주세요|해주시기|해주시길|해주시면|해주십시오|"
    r"되겠습니다|되었습|되었으면|되면|되어|되었습니다|되는데|않습니다|않아요|"
    r"같습니다|하겠습니다|부탁드립니다|감사합니다|감사하겠습니다|해요|했어요|합니다만)$"
)
def strip_suffix(tok: str) -> str:
    return re.sub(_SUFFIX_PAT, "", tok)
def tokenize_ko(s: str):
    if not isinstance(s, str):
        return []
    cand = re.findall(r"[가-힣A-Za-z0-9]+", s)
    out = []
    for t in cand:
        t = strip_suffix(t)
        if len(t) < 2:
            continue
        if t in _STOPWORDS:
            continue
        out.append(t)
    return out
def make_bigrams(tokens, join_str=" "):
    return [join_str.join(p) for p in zip(tokens, tokens[1:])]
def build_wordcloud_image(
    fb_df, date_filter=None, use_bigrams=False, font_path="data/Nanum_Gothic/NanumGothic-Regular.ttf"
):
    if not WORDCLOUD_AVAILABLE:
        return None
    if fb_df is None or fb_df.empty or "feedback" not in fb_df.columns:
        return None
    df = fb_df.copy()
    if date_filter is not None and "date" in df.columns:
        df = df[df["date"].astype(str) == str(date_filter)]
    texts = df["feedback"].dropna().astype(str).tolist()
    if not texts:
        return None
    counter = Counter()
    for t in texts:
        toks = tokenize_ko(t)
        if use_bigrams:
            toks = make_bigrams(toks)
        counter.update(toks)
    if not counter:
        return None
    fp = font_path if Path(font_path).exists() else None
    from wordcloud import WordCloud as _WC
    wc = _WC(font_path=fp, width=1200, height=600, background_color="white", colormap="tab20c")
    return wc.generate_from_frequencies(counter).to_image()
def load_feedback(path="data/feedback.csv"):
    p = Path(path)
    if not p.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(p)
    except Exception:
        return pd.DataFrame()


# ====================== 4) 뉴스 카드 렌더링 헬퍼 ==============================
URL_RE = re.compile(r"https?://[^\s,]+", re.I)
def _first_url(s: str) -> str | None:
    if not isinstance(s, str):
        return None
    m = URL_RE.findall(s)
    return m[0] if m else None
def _domain(u: str) -> str:
    try:
        h = urlparse(u).netloc
        return h.replace("www.", "")
    except Exception:
        return ""
def render_news_cards_for_event(df_all: pd.DataFrame, row: pd.Series):
    st.markdown("###### 집회/시위 관련 기사 보기")
    d, stt, edt = row["_date"], row["_start"], row["_end"]
    rows = df_all[(df_all["_date"] == d) & (df_all["_start"] == stt) & (df_all["_end"] == edt)][
        ["__link", "__title"]
    ].dropna(how="all")
    items, seen = [], set()
    for _, r in rows.iterrows():
        url = _first_url(str(r["__link"]))
        title = str(r["__title"]).strip()
        if not url or not title:
            continue
        if url in seen:
            continue
        seen.add(url)
        items.append({"url": url, "title": title})
    st.markdown("<div class='news-wrap'>", unsafe_allow_html=True)
    if not items:
        st.caption("해당 시간대의 관련 기사를 찾지 못했습니다.")
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<div class='gap-24'></div>", unsafe_allow_html=True)
        return
    html_parts = ["<div class='news-grid'>"]
    for it in items[:8]:
        url = it["url"]
        title = html.escape(it["title"])
        dom = _domain(url)
        meta = f"{dom} · {d:%Y.%m.%d}"
        card = (
            "<div class='news-card'>"
            f"<div class='news-title'>{title}</div>"
            f"<div class='news-meta'>{meta}"
            f"<a class='news-link' href='{url}' target='_blank' rel='noopener'>원문 보기 ↗</a>"
            "</div></div>"
        )
        html_parts.append(card)
    html_parts.append("</div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div class='gap-24'></div>", unsafe_allow_html=True)


# ====================== 5) 상세 페이지(일자) ==================================
def render_detail(df_all: pd.DataFrame, bus_df: pd.DataFrame, routes_df: pd.DataFrame, d: date, idx: int):
    day_df = filter_by_day(df_all, d)
    if len(day_df) == 0 or idx < 0 or idx >= len(day_df):
        st.error("상세 정보를 찾을 수 없어요.")
        if st.button("← 목록으로"):
            st.query_params.clear()
            st.rerun()
        return
    if st.button("← 목록으로"):
        st.query_params.clear()
        st.rerun()
    row = day_df.iloc[idx]
    WEEK_KO = ["월", "화", "수", "목", "금", "토", "일"]
    st.markdown(f"#### {d.month}월 {d.day}일({WEEK_KO[d.weekday()]}) 상세 정보")
    st.markdown("###### 오늘의 집회/시위")
    time_str = f"{row['_start']} ~ {row['_end']}"
    loc_str = f"{(row['_dist']+' ') if row['_dist'] not in ['','nan','None'] else ''}{row['_loc']}"
    if pd.notna(row["_head"]) and str(row["_head"]).strip() != "":
        try:
            head_str = f"{int(row['_head'])}명"
        except Exception:
            head_str = f"{row['_head']}명"
    else:
        head_str = ""
    keywords = str(row["_memo"]).strip() if str(row["_memo"]).strip() not in ["nan", "None"] else ""
    info_df = pd.DataFrame([[time_str, loc_str, head_str, keywords]], columns=["집회 시간", "집회 장소(행진로)", "신고 인원", "관련 이슈"])
    st.table(info_df)
    st.markdown("###### 버스 우회 정보")
    bus_rows = get_bus_rows_for_date(bus_df, d)
    route_slice = routes_df[routes_df["date"] == d].copy() if routes_df is not None and not routes_df.empty else pd.DataFrame()
    if bus_rows.empty:
        st.caption("※ 해당 날짜의 버스 우회 정보가 없습니다.")
    else:
        if not route_slice.empty:
            agg = (
                route_slice.dropna(subset=["ars_id", "route"])
                .groupby("ars_id")["route"]
                .apply(lambda s: ", ".join(sorted(set(s))))
            ).rename("노선")
            bus_rows = bus_rows.merge(agg, left_on="ARS_ID", right_index=True, how="left")
        else:
            bus_rows["노선"] = ""
        bus_view = bus_rows[["ARS_ID", "정류소명", "노선"]].rename(columns={"ARS_ID": "버스 정류소 번호", "정류소명": "버스 정류소 명"})
        bus_view = bus_view[["버스 정류소 번호", "버스 정류소 명", "노선"]]
        st.table(bus_view.reset_index(drop=True))
        map_df = bus_rows[["lat", "lon", "정류소명", "ARS_ID", "노선"]].copy()
        if not map_df.empty:
            view_state = pdk.ViewState(latitude=float(map_df["lat"].mean()), longitude=float(map_df["lon"].mean()), zoom=16)
            point_layer = pdk.Layer(
                "ScatterplotLayer",
                data=map_df,
                get_position="[lon, lat]",
                get_radius=25,
                get_fill_color=[0, 122, 255, 200],
                pickable=True,
            )
            tooltip = {"html": "<b>{정류소명}</b><br/>정류소 번호: {ARS_ID}<br/>노선: {노선}", "style": {"backgroundColor": "white", "color": "black"}}
            st.pydeck_chart(pdk.Deck(layers=[point_layer], initial_view_state=view_state, tooltip=tooltip, map_style="road"))
    render_news_cards_for_event(df_all, row)
    st.markdown("###### 오늘의 집회/시위에 대한 여러분의 건의사항을 남겨주세요")
    with st.form("feedback_form", clear_on_submit=True):
        fb = st.text_area("의견을 작성해주세요 (관리자에게 전달됩니다)", height=80, key="fb_detail")
        submitted = st.form_submit_button("등록")
    if submitted:
        if not fb.strip():
            st.warning("내용을 입력해주세요.")
        else:
            save_path = Path("data/feedback.csv")
            save_path.parent.mkdir(parents=True, exist_ok=True)
            from hashlib import md5
            row_key = f"{str(d)}|{row.get('_start')}|{row.get('_end')}|{row.get('_loc')}|{fb.strip()}"
            dupe_key = md5(row_key.encode("utf-8")).hexdigest()
            df_now = load_feedback(str(save_path))
            if "dupe_key" not in df_now.columns:
                df_now["dupe_key"] = ""
            if dupe_key in set(df_now["dupe_key"].astype(str)):
                st.info("이미 같은 내용이 저장되어 있습니다.")
            else:
                row_dict = {
                    "saved_at": datetime.now().isoformat(timespec="seconds"),
                    "date": str(d),
                    "start": row.get("_start", ""),
                    "end": row.get("_end", ""),
                    "location": row.get("_loc", ""),
                    "district": row.get("_dist", ""),
                    "reported_head": row.get("_head", ""),
                    "memo": row.get("_memo", ""),
                    "feedback": fb.strip(),
                    "dupe_key": dupe_key,
                }
                pd.concat([df_now, pd.DataFrame([row_dict])], ignore_index=True).to_csv(save_path, index=False, encoding="utf-8-sig")
                st.success("건의사항이 저장되었습니다. 감사합니다!")
    st.markdown("###### 건의사항 키워드 요약")
    fb_all = load_feedback("data/feedback.csv")
    if fb_all.empty:
        st.caption("아직 저장된 건의사항이 없습니다.")
    else:
        only_today = st.toggle("이 날짜만 보기", value=True, key="wc_today_only")
        use_bigrams = st.toggle("연결어(2단어)로 보기", value=False, key="wc_bigram_only")
        img = build_wordcloud_image(
            fb_all,
            date_filter=d if only_today else None,
            use_bigrams=use_bigrams,
            font_path="data/Nanum_Gothic/NanumGothic-Regular.ttf"
        )
        if img is not None:
            st.image(img, use_container_width=True)
        else:
            st.caption("워드클라우드 데이터가 부족합니다.")


# ====================== 6) 메인(월간) 화면 ====================================
CALENDAR_H = 520
HEADER_OFFSET = 85
PANEL_BODY_H = CALENDAR_H - HEADER_OFFSET
def render_main_page(df, bus_df, routes_df):
    st.markdown("### 이달의 집회")
    st.caption("이번 달의 집회를 한눈에 확인해보세요.")
    left, right = st.columns(2)
    # --- 왼쪽: 달력
    with left:
        with st.container(border=True):
            events = df_to_month_dots(df)
            options = {
                "initialView": "dayGridMonth",
                "locale": "ko",
                "height": CALENDAR_H,
                "firstDay": 0,
                "headerToolbar": {"left": "prev", "center": "title", "right": "next"},
                "buttonIcons": {"prev": "", "next": ""},
                "dayMaxEventRows": True,
            }
            cal_res = calendar(
                events=events,
                options=options,
                custom_css="""
/* ===== FullCalendar – Light theme override inside the widget iframe ===== */
.fc, .fc .fc-scrollgrid, .fc .fc-daygrid, .fc-theme-standard .fc-scrollgrid {
  background:#ffffff !important; color:#111827 !important;
}
.fc-theme-standard td, .fc-theme-standard th { border-color:#e5e7eb !important; }
.fc .fc-toolbar-title { color:#111827 !important; font-weight:700 !important; }
.fc .fc-daygrid-day-number { color:#111827 !important; }
.fc .fc-day-today { background:#fff7ed !important; }
.fc .fc-daygrid-more-link, .fc .fc-event { color:#111827 !important; }
/* 상단 prev/next 버튼 */
.fc .fc-button { background:#fff !important; border:1px solid #000 !important; color:#000 !important; border-radius:20px !important; }
.fc .fc-icon { display:none !important; }
.fc .fc-prev-button:after { content:"◀"; font-size:16px; }
.fc .fc-next-button:after { content:"▶"; font-size:16px; }
/* 'more' 두 줄 처리 + 텍스트 크기 축소 */
.fc-daygrid-more-link { white-space: pre-line !important; font-size:12px !important; line-height:1.2 !important; }
.fc-daygrid-more-link::before { content: attr(aria-label); white-space: pre-line; }
/* 팝오버 안의 각 이벤트 텍스트 크기 축소 */
.fc-popover .fc-event-title, .fc-popover .fc-event-time { font-size:12px !important; }
"""
            )
            if cal_res and cal_res.get("eventClick"):
                try:
                    ev = cal_res["eventClick"]["event"]
                    ep = ev.get("extendedProps", {})
                    d = parser.parse(ep.get("d", "")).date()
                    stime = ep.get("st", "")
                    etime = ep.get("ed", "")
                    loc = ep.get("loc", "")
                    day_df = filter_by_day(df, d)
                    idx = 0
                    for i, (_, rr) in enumerate(day_df.iterrows()):
                        if rr["_start"] == stime and rr["_end"] == etime and rr["_loc"] == loc:
                            idx = i
                            break
                    st.query_params.clear()
                    st.query_params["view"] = "detail"
                    st.query_params["date"] = d.isoformat()
                    st.query_params["idx"] = str(idx)
                    st.rerun()
                except Exception:
                    pass
    # --- 오른쪽: 일자 리스트
    if "sel_date" not in st.session_state:
        st.session_state.sel_date = date.today()
    with right:
        with st.container(border=True):
            nav1, nav2, nav3 = st.columns([1, 1, 1])
            with nav1:
                if st.button("◀", use_container_width=True):
                    d = st.session_state.sel_date
                    st.session_state.sel_date = d.fromordinal(d.toordinal() - 1)
            with nav2:
                if st.button("오늘", use_container_width=True):
                    st.session_state.sel_date = date.today()
            with nav3:
                if st.button("▶", use_container_width=True):
                    d = st.session_state.sel_date
                    st.session_state.sel_date = d.fromordinal(d.toordinal() + 1)
            sel_date = st.session_state.sel_date
            WEEK_KO = ["월", "화", "수", "목", "금", "토", "일"]
            st.markdown(f"#### {sel_date.month}월 {sel_date.day}일({WEEK_KO[sel_date.weekday()]}) 집회 일정 안내")
            day_df = filter_by_day(df, sel_date)
            html_parts = [f"<div style='height:{PANEL_BODY_H}px; overflow-y:auto; padding-right:8px;'>"]
            if len(day_df) == 0:
                html_parts.append('<div class="sub">등록된 집회가 없습니다.</div>')
            else:
                for i, (_, r) in enumerate(day_df.iterrows()):
                    loc_line = r["_loc"]
                    if r["_dist"] and str(r["_dist"]).strip() not in ["nan", "None", ""]:
                        loc_line = f"{r['_dist']}  {loc_line}"
                    metas = []
                    if pd.notna(r["_head"]) and str(r["_head"]).strip() != "":
                        try:
                            metas.append(f"신고 인원 {int(r['_head'])}명")
                        except Exception:
                            metas.append(f"신고 인원 {r['_head']}명")
                    if r["_memo"] and str(r["_memo"]).strip() not in ["nan", "None", ""]:
                        metas.append(str(r["_memo"]))
                    meta_text = " · ".join(metas)
                    meta_html = f"<div class='meta'>{meta_text}</div>" if meta_text else ""
                    href = f"?view=detail&date={sel_date.isoformat()}&idx={i}"
                    html_parts.append(
                        textwrap.dedent(
                            f"""
                            <a class="card-link" href="{href}">
                              <div class="card">
                                <div class="time">{r["_start"]} ~ {r["_end"]}</div>
                                <div class="sub">{loc_line}</div>
                                {meta_html}
                              </div>
                            </a>
                            """
                        ).strip()
                    )
            html_parts.append("</div>")
            st.markdown("\n".join(html_parts), unsafe_allow_html=True)


# ====================== 7) 챗봇 (모달 + FAB) ==================================
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "input_counter" not in st.session_state:
    st.session_state.input_counter = 0

def _chat_ui_body():
    st.markdown('<div class="chat-wrap"><div class="chat-scroll" id="chat-scroll">', unsafe_allow_html=True)
    if not st.session_state.chat_history:
        st.session_state.chat_history.append(("bot", "안녕하세요! 날짜와 노선을 알려주시면 우회 정보를 찾아드릴게요.\n예) 8월 15일 172번 우회 알려줘"))
    for role, msg in st.session_state.chat_history:
        row_cls = "msg-row user" if role == "user" else "msg-row"
        bub_cls = "bubble user" if role == "user" else "bubble bot"
        st.markdown(f'<div class="{row_cls}"><div class="{bub_cls}">{msg}</div></div>', unsafe_allow_html=True)
    st.markdown("</div></div>", unsafe_allow_html=True)
    st.markdown('<div class="chat-input-area">', unsafe_allow_html=True)
    c1, c2 = st.columns([8, 1])
    with c1:
        user_input = st.text_input(
            "예: 8월 15일의 172번 버스 우회 정보를 알려줘",
            key=f"chat_input_{st.session_state.input_counter}",
            label_visibility="collapsed",
        )
    with c2:
        send = st.button("전송", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
    if send and user_input.strip():
        st.session_state.chat_history.append(("user", user_input))
        if all_texts:
            llm = ChatOpenAI(model_name="gpt-4o-mini", api_key=API_KEY)
            prompt_template = PromptTemplate(
                input_variables=["context", "question"],
                template="""
당신은 주어진 텍스트를 기반으로 질문에 답하는 Q&A 챗봇입니다.

{context}

---
질문: {question}
답변(텍스트 기반으로만, 사실에 맞게 작성):
""",
            )
            prompt = prompt_template.format(context=all_texts, question=user_input)
            with st.spinner("답변 작성 중..."):
                response = llm.predict(prompt)
        else:
            response = "❌ 텍스트 데이터가 없어서 답변할 수 없습니다."
        st.session_state.chat_history.append(("bot", response))
        st.session_state.input_counter += 1
        st.rerun()

_dialog = getattr(st, "dialog", None) or getattr(st, "experimental_dialog", None)
def render_chat_modal_if_needed():
    qp = st.query_params
    if qp.get("chat", "") == "open" and _dialog is not None:
        @_dialog("버스 우회 정보 챗봇")
        def _modal():
            _chat_ui_body()
            col1, col2 = st.columns([1,1])
            with col1:
                if st.button("닫기", use_container_width=True):
                    params = dict(qp)
                    params.pop("chat", None)
                    st.query_params.clear()
                    for k, v in params.items():
                        st.query_params[k] = v
                    st.rerun()
            with col2:
                st.caption("도움이 더 필요하시면 계속 질문해 주세요!")
        _modal()
def render_chat_fab():
    qp = st.query_params
    pairs = [f"{k}={v}" for k, v in qp.items() if k != "chat"]
    pairs.append("chat=open")
    href = "?" + "&".join(pairs) if pairs else "?chat=open"
    st.markdown(f"<a class='fab-chat' href='{href}' title='챗봇 열기'>💬</a>", unsafe_allow_html=True)


# ====================== 8) 라우팅/데이터 경로 ================================
DATA_PATH = st.sidebar.text_input("집회 데이터 경로 (xlsx/csv)", value="data/protest_data.xlsx")
BUS_PATH = st.sidebar.text_input("버스 우회 데이터 경로 (xlsx)", value="data/bus_data.xlsx")
ROUTES_PATH = st.sidebar.text_input("버스 노선 데이터 경로 (CSV: routes_final.csv)", value="routes_final.csv")

# 새로고침 버튼(캐시 클리어)
if st.sidebar.button("데이터 새로고침"):
    st.cache_data.clear()
    st.rerun()

@st.cache_data
def load_all_txt(data_dir="data/chatbot"):
    texts=[]; p=Path(data_dir)
    if not p.exists(): return ""
    for path in p.glob("*.txt"):
        try:
            with open(path,"r",encoding="utf-8") as f: texts.append(f.read())
        except Exception as e: st.warning(f"{path} 읽기 오류: {e}")
    return "\n\n".join(texts)
all_texts = load_all_txt()

# 데이터 로드 (파일 mtime을 캐시 키로 포함)
try:
    df        = load_events(DATA_PATH,  os.path.getmtime(DATA_PATH))
    bus_df    = load_bus(BUS_PATH,      os.path.getmtime(BUS_PATH) if Path(BUS_PATH).exists() else 0.0)
    routes_df = load_routes(ROUTES_PATH, os.path.getmtime(ROUTES_PATH) if Path(ROUTES_PATH).exists() else 0.0)
except Exception as e:
    st.error(f"데이터 로드 오류: {e}")
    st.stop()

# 라우팅
qp = st.query_params
if qp.get("view", "") == "detail":
    try:
        d_sel = parser.parse(qp.get("date", "")).date()
        idx_sel = int(qp.get("idx", "0"))
        render_detail(df, bus_df, routes_df, d_sel, idx_sel)
    except Exception:
        st.warning("잘못된 링크입니다. 목록으로 돌아갑니다.")
        st.query_params.clear()
else:
    render_main_page(df, bus_df, routes_df)

# FAB + 모달 처리
render_chat_fab()
render_chat_modal_if_needed()

# ====================== 9) 푸터 ===============================================
jongno_logo = get_base64_of_image("data/assets/jongno_logo.png")
kt_logo = get_base64_of_image("data/assets/kt_logo.png")
st.markdown(
    f"""
<style>
.site-footer {{ margin-top:200px; border:1px solid #e5e7eb; border-radius:6px; overflow:hidden; }}
.site-footer .footer-top {{
  background:#575757; color:#ffffff; text-align:center; padding:22px 16px 20px 16px; line-height:1.5; font-size:15px;
}}
.site-footer .footer-top .title {{ font-weight:700; letter-spacing:0.2px; margin-bottom:4px; display:block; }}
.site-footer .footer-top .copy  {{ font-size:13px; opacity:0.95; }}
.site-footer .footer-bottom {{
  background:#ffffff; padding:18px 22px; display:flex; align-items:center; justify-content:space-between; gap:16px;
}}
.site-footer .bottom-left {{ color:#111827; font-size:14px; line-height:1.6; }}
.site-footer .bottom-left .who {{ font-weight:700; margin-bottom:4px; }}
.site-footer .bottom-right {{ display:flex; align-items:center; gap:22px; }}
.site-footer .bottom-right img {{ height:40px; display:block; }}
@media (max-width: 720px) {{
  .site-footer .footer-bottom {{ flex-direction: column; align-items: flex-start; gap: 12px; }}
}}
</style>

<div class="site-footer">
  <div class="footer-top">
    <span class="title">종로구청 × KT디지털인재장학생 5조</span>
    <span class="copy">© 2025 KT디지털인재장학생 5조 All rights reserved</span>
  </div>

  <div class="footer-bottom">
    <div class="bottom-left">
      <div class="who">서비스를 제작한 사람들</div>
      <div>KT 디지털인재장학생 | 강혜선 김민영 변예원 이은서 장진영 한태희</div>
    </div>
    <div class="bottom-right">
      <img src="data:image/png;base64,{jongno_logo}" alt="종로구 로고" />
      <img src="data:image/png;base64,{kt_logo}" alt="KT 로고" />
    </div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)
