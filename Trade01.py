import streamlit as st
import pandas as pd
import plotly.express as px

# 1. 타이틀: 🌐무역 분석 대시보드[cite: 2]
st.set_page_config(page_title="무역 분석 대시보드", layout="wide")
st.title("무역 분석 대시보드")

@st.cache_data
def load_data():
    # 데이터 로드[cite: 2]
    baci = pd.read_csv('baci_85_sample.csv')
    codes = pd.read_csv('country_codes_sample.csv')
    
    # 2. baci_85_sample.csv의 결측치 처리[cite: 2]
    baci = baci.dropna()
    
    # 데이터 병합 (j: 대상 국가 코드)
    df = pd.merge(baci, codes, on='j', how='left')
    df['country_name'] = df['country_name'].fillna('알 수 없음')
    
    # 무역액 등급(대, 중, 소) 파생변수 생성 (v: 수출액)[cite: 2]
    q33 = df['v'].quantile(0.33)
    q66 = df['v'].quantile(0.66)
    
    def assign_grade(val):
        if val <= q33: return '소'
        elif val <= q66: return '중'
        else: return '대'
        
    df['trade_grade'] = df['v'].apply(assign_grade)
    
    return df

df = load_data()

# ------------------- 사이드바: 필터 -------------------
st.sidebar.header("필터 설정")

# 국가 선택, 무역액 등급 선택(대,중,소) 필터[cite: 2]
country_list = sorted(df['country_name'].unique().tolist())
selected_countries = st.sidebar.multiselect("국가 선택 (한글명)", country_list, default=country_list[:5])

grade_list = ['대', '중', '소']
selected_grades = st.sidebar.multiselect("무역액 등급 선택", grade_list, default=grade_list)

# 필터 적용
filtered_df = df[
    (df['country_name'].isin(selected_countries)) & 
    (df['trade_grade'].isin(selected_grades))
]

# ------------------- 오른쪽 화면 (메인) -------------------

# 3. 총거래 건수 / 총 수출액(달러)[cite: 2]
col1, col2 = st.columns(2)
with col1:
    st.metric(label="총 거래 건수", value=f"{len(filtered_df):,} 건")
with col2:
    st.metric(label="총 수출액 (달러)", value=f"${filtered_df['v'].sum():,.2f}")
    
st.markdown("---")

# 4. 국가*연도 수출액 히트맵 (상위 8개국) / 무역액 등급분포[cite: 2]
row1_col1, row1_col2 = st.columns(2)

with row1_col1:
    st.subheader("국가별/연도별 수출액 히트맵 (상위 8개국)")
    # 전체 데이터 기준 상위 8개국 추출
    top_8_countries = df.groupby('country_name')['v'].sum().nlargest(8).index
    heatmap_data = df[df['country_name'].isin(top_8_countries)]
    heatmap_pivot = heatmap_data.groupby(['country_name', 't'])['v'].sum().reset_index()
    
    fig_heatmap = px.density_heatmap(
        heatmap_pivot, x='t', y='country_name', z='v',
        labels={'t': '연도', 'country_name': '국가', 'v': '수출액'},
        color_continuous_scale="Viridis"
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)

with row1_col2:
    st.subheader("무역액 등급 분포")
    # 필터링된 데이터의 등급 분포 (가로 막대 그래프)
    grade_dist = filtered_df['trade_grade'].value_counts().reindex(['소', '중', '대']).reset_index()
    grade_dist.columns = ['무역액 등급', '건수']
    grade_dist['건수'] = grade_dist['건수'].fillna(0)
    
    fig_bar = px.bar(
        grade_dist, 
        x='건수', 
        y='무역액 등급', 
        orientation='h',
        text='건수',
        color='무역액 등급',
        color_discrete_map={'대': '#EF553B', '중': '#636EFA', '소': '#00CC96'},
        labels={'건수': '거래 건수', '무역액 등급': '등급'}
    )
    fig_bar.update_traces(texttemplate='%{text:,}건', textposition='outside')
    fig_bar.update_layout(showlegend=False, yaxis={'categoryorder': 'array', 'categoryarray': ['소', '중', '대']})
    st.plotly_chart(fig_bar, use_container_width=True)
    
st.markdown("---")

# 5. 상위 5개국 * 무역액 등급 교차표 (원본건수 / 정규화비율)[cite: 2]
st.subheader("상위 5개국 무역액 등급 교차표")

# 전체 데이터 기준 상위 5개국 추출
top_5_countries = df.groupby('country_name')['v'].sum().nlargest(5).index
cross_df = df[df['country_name'].isin(top_5_countries)]

row2_col1, row2_col2 = st.columns(2)

with row2_col1:
    st.markdown("**원본 건수**")
    crosstab_raw = pd.crosstab(cross_df['country_name'], cross_df['trade_grade'])
    
    # 등급 컬럼 순서 정렬 및 없는 등급 0으로 채우기
    for col in ['대', '중', '소']:
        if col not in crosstab_raw.columns:
            crosstab_raw[col] = 0
    crosstab_raw = crosstab_raw[['대', '중', '소']]
    st.dataframe(crosstab_raw, use_container_width=True)
    
with row2_col2:
    st.markdown("**정규화 비율 (행 기준 백분율)**")
    crosstab_norm = pd.crosstab(cross_df['country_name'], cross_df['trade_grade'], normalize='index') * 100
    
    for col in ['대', '중', '소']:
        if col not in crosstab_norm.columns:
            crosstab_norm[col] = 0.0
    crosstab_norm = crosstab_norm[['대', '중', '소']]
    st.dataframe(crosstab_norm.style.format("{:.2f}%"), use_container_width=True)