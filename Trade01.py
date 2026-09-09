import streamlit as st
import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt
import seaborn as sns

# 한글 폰트 설정 (환경에 맞게 수정: Windows는 'Malgun Gothic', Mac은 'AppleGothic')
plt.rc('font', family='Malgun Gothic')
plt.rcParams['axes.unicode_minus'] = False

# 페이지 레이아웃 넓게 설정
st.set_page_config(layout="wide", page_title="무역 분석 대시보드")

# 1. 타이틀: 무역 분석 대시보드
st.title("무역 분석 대시보드")

@st.cache_data
def load_data():
    # 데이터 불러오기
    baci_df = pd.read_csv("baci_85_sample.csv")
    codes_df = pd.read_csv("country_codes_sample.csv")
    
    # 2. baci_85_sample.csv의 결측치 처리
    baci_df = baci_df.dropna()
    
    # --- 자동 컬럼 매핑 로직 ---
    # BACI 데이터의 국가 코드 컬럼 감지 (일반적으로 'i' 또는 'country_code')
    baci_target_col = 'i' if 'i' in baci_df.columns else ('country_code' if 'country_code' in baci_df.columns else baci_df.columns[0])
    
    # 국가 코드 데이터의 매핑용 코드 컬럼 감지 ('country_code', 'code' 등)
    codes_target_col = 'country_code' if 'country_code' in codes_df.columns else ('code' if 'code' in codes_df.columns else codes_df.columns[0])
    
    # 국가명 컬럼 감지 ('country_name_abbreviation', 'country_name', 'country' 등)
    if 'country_name_abbreviation' in codes_df.columns:
        codes_name_col = 'country_name_abbreviation'
    elif 'country_name' in codes_df.columns:
        codes_name_col = 'country_name'
    elif 'country' in codes_df.columns:
        codes_name_col = 'country'
    else:
        codes_name_col = codes_df.columns[1] if len(codes_df.columns) > 1 else codes_df.columns[0]

    # 데이터 병합
    df = pd.merge(baci_df, codes_df, left_on=baci_target_col, right_on=codes_target_col, how='left')
        
    # 가상의 컬럼 이름 설정 (실제 데이터에 맞게 수정)
    df['export_value'] = df['v'] if 'v' in df.columns else (df['export_value'] if 'export_value' in df.columns else 0)
    # 병합된 국가명이 없을 경우 'Unknown'으로 처리
    df['country_name'] = df[codes_name_col].fillna('Unknown')
    df['year'] = df['t'] if 't' in df.columns else (df['year'] if 'year' in df.columns else 2020)

    # 무역액 등급 (대, 중, 소) 임의 기준 부여 (3분위수 기준, 중복값 에러 방지를 위해 rank 사용)
    df['trade_tier'] = pd.qcut(df['export_value'].rank(method='first'), q=3, labels=['소', '중', '대'])
    
    return df

df = load_data()

# --- 사이드바 ---
st.sidebar.header("필터 설정")

# 국가 선택 필터 (Unknown이 아닌 국가들만 기본으로 선택되도록 처리)
country_list = df['country_name'].unique().tolist()
valid_countries = [c for c in country_list if c != 'Unknown']
default_selection = valid_countries[:5] if valid_countries else country_list[:5]

selected_countries = st.sidebar.multiselect("국가 선택", options=country_list, default=default_selection)

# 무역액 등급 선택 (대, 중, 소)
tier_list = ['대', '중', '소']
selected_tiers = st.sidebar.multiselect("무역액 등급 선택", options=tier_list, default=tier_list)

# 필터링 적용
filtered_df = df[
    (df['country_name'].isin(selected_countries)) & 
    (df['trade_tier'].isin(selected_tiers))
]

# --- 메인 화면 (오른쪽) ---

# 3. 총거래 건수 및 총 수출액(달러)
col1, col2 = st.columns(2)
with col1:
    st.metric(label="총거래 건수", value=f"{len(filtered_df):,} 건")
with col2:
    total_export = filtered_df['export_value'].sum()
    st.metric(label="총 수출액(달러)", value=f"${total_export:,.2f}")

st.markdown("---")

# 4. 국가*연도 수출액 히트맵(상위 8개국) & 무역액 등급분포
col3, col4 = st.columns(2)

with col3:
    st.subheader("국가*연도 수출액 히트맵 (상위 8개국)")
    # 상위 8개국 추출
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

# 5. 상위 5개국 * 무역액 등급 교차표 (원본건수 / 정규화비율)
st.subheader("상위 5개국 * 무역액 등급 교차표")
# 상위 5개국 추출
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