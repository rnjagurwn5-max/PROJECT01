import streamlit as st
import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt
import seaborn as sns

# 한글 폰트 설정
plt.rc('font', family='Malgun Gothic')
plt.rcParams['axes.unicode_minus'] = False

# 페이지 레이아웃 넓게 설정
st.set_page_config(layout="wide", page_title="무역 분석 대시보드")
st.title("무역 분석 대시보드")

# --- 1. 파일 불러오기 및 실제 컬럼명 화면 출력 (디버깅용) ---
@st.cache_data
def load_raw_data():
    return pd.read_csv("baci_85_sample.csv"), pd.read_csv("country_codes_sample.csv")

baci_df, codes_df = load_raw_data()
baci_df = baci_df.dropna()

# 화면 상단에 실제 컬럼명 표시
st.info(f"📌 BACI 데이터 컬럼명: {baci_df.columns.tolist()}")
st.info(f"📌 국가코드 데이터 컬럼명: {codes_df.columns.tolist()}")
st.warning("💡 위 파란색 박스에 뜬 컬럼명을 확인하시고, 코드 안의 '핵심 수정 포인트' 부분을 실제 이름으로 바꿔주세요.")

# --- 2. ★ 여기가 핵심 수정 포인트입니다 ★ ---
# 아래 세 줄의 ' ' 안의 텍스트를 위 파란색 박스에서 확인한 실제 이름으로 변경해 주세요.
baci_col = 'i'             # BACI 파일에서 수출국 코드를 의미하는 컬럼 (예: 'i', 'country_code' 등)
codes_col = 'country_code' # 국가코드 파일에서 매핑용 코드를 의미하는 컬럼 (예: 'country_code', 'code' 등)
name_col = 'country_name'  # 국가코드 파일에서 실제 국가명을 의미하는 컬럼 (예: 'country_name_abbreviation', 'country_name' 등)
# ----------------------------------------------

@st.cache_data
def process_data(baci, codes, b_col, c_col, n_col):
    df = baci.copy()
    
    # 입력한 컬럼명이 실제 데이터에 존재하는지 확인 후 병합
    if b_col in df.columns and c_col in codes.columns:
        df[b_col] = df[b_col].astype(str)
        codes[c_col] = codes[c_col].astype(str)
        df = pd.merge(df, codes, left_on=b_col, right_on=c_col, how='left')
        df['country_name'] = df[n_col].fillna('Unknown') if n_col in df.columns else 'Unknown'
    else:
        df['country_name'] = 'Unknown'

    # 필수 변수 매핑 (수출액, 연도)
    df['export_value'] = df['v'] if 'v' in df.columns else (df['export_value'] if 'export_value' in df.columns else 0)
    df['year'] = df['t'] if 't' in df.columns else (df['year'] if 'year' in df.columns else 2020)

    # 무역액 등급 설정
    df['trade_tier'] = pd.qcut(df['export_value'].rank(method='first'), q=3, labels=['소', '중', '대'])
    return df

df = process_data(baci_df, codes_df, baci_col, codes_col, name_col)

# --- 사이드바 ---
st.sidebar.header("필터 설정")

# 국가 선택 필터 (Unknown 제외 로직 강화)
country_list = df['country_name'].dropna().unique().tolist()
valid_countries = [c for c in country_list if c != 'Unknown']

# 만약 매핑이 실패해서 리스트가 비어있다면 Unknown이라도 표시하여 에러 방지
if not valid_countries:
    valid_countries = country_list

default_selection = valid_countries[:5] if len(valid_countries) >= 5 else valid_countries
selected_countries = st.sidebar.multiselect("국가 선택", options=valid_countries, default=default_selection)

# 무역액 등급 선택
tier_list = ['대', '중', '소']
selected_tiers = st.sidebar.multiselect("무역액 등급 선택", options=tier_list, default=tier_list)

# 필터링 적용
filtered_df = df[
    (df['country_name'].isin(selected_countries)) & 
    (df['trade_tier'].isin(selected_tiers))
]

# --- 메인 화면 (오른쪽) ---
col1, col2 = st.columns(2)
with col1:
    st.metric(label="총거래 건수", value=f"{len(filtered_df):,} 건")
with col2:
    total_export = filtered_df['export_value'].sum()
    st.metric(label="총 수출액(달러)", value=f"${total_export:,.2f}")

st.markdown("---")

col3, col4 = st.columns(2)

with col3:
    st.subheader("국가*연도 수출액 히트맵 (상위 8개국)")
    top8_countries = filtered_df.groupby('country_name')['export_value'].sum().nlargest(8).index
    df_top8 = filtered_df[filtered_df['country_name'].isin(top8_countries)]
    
    if not df_top8.empty:
        pivot_df = df_top8.pivot_table(index='country_name', columns='year', values='export_value', aggfunc='sum')
        fig, ax = plt.subplots(figsize=(8, 6))
        sns.heatmap(pivot_df, cmap='YlGnBu', annot=False, ax=ax)
        plt.ylabel("국가")
        plt.xlabel("연도")
        st.pyplot(fig)
    else:
        st.info("조건에 맞는 데이터가 없습니다.")

with col4:
    st.subheader("무역액 등급분포")
    if not filtered_df.empty:
        tier_counts = filtered_df['trade_tier'].value_counts().reset_index()
        tier_counts.columns = ['무역액 등급', '건수']
        fig_pie = px.pie(tier_counts, names='무역액 등급', values='건수', hole=0.3, color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("조건에 맞는 데이터가 없습니다.")

st.markdown("---")

st.subheader("상위 5개국 * 무역액 등급 교차표")
top5_countries = filtered_df.groupby('country_name')['export_value'].sum().nlargest(5).index
df_top5 = filtered_df[filtered_df['country_name'].isin(top5_countries)]

col5, col6 = st.columns(2)
if not df_top5.empty:
    with col5:
        st.markdown("**원본건수**")
        cross_tab_count = pd.crosstab(df_top5['country_name'], df_top5['trade_tier'])
        st.dataframe(cross_tab_count, use_container_width=True)

    with col6:
        st.markdown("**정규화비율**")
        cross_tab_norm = pd.crosstab(df_top5['country_name'], df_top5['trade_tier'], normalize='index')
        st.dataframe(cross_tab_norm.style.format("{:.2%}"), use_container_width=True)
else:
    st.info("조건에 맞는 데이터가 없습니다.")