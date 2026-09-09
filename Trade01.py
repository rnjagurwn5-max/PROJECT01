import streamlit as st
import pandas as pd
import plotly.express as px

# 1. 타이틀: 무역 분석 대시보드[cite: 1]
st.set_page_config(page_title="무역 분석 대시보드", layout="wide")
st.title("무역 분석 대시보드")

# 데이터 로드 및 전처리 함수
@st.cache_data
def load_data():
    # 데이터 불러오기[cite: 1]
    # 실제 환경에서는 파일 경로를 확인하세요. 
    try:
        baci = pd.read_csv('baci_85_sample.csv')
        codes = pd.read_csv('country_codes_sample.csv')
    except FileNotFoundError:
        st.error("데이터 파일을 찾을 수 없습니다. baci_85_sample.csv와 country_codes_sample.csv가 같은 폴더에 있는지 확인하세요.")
        return pd.DataFrame()

    # 2. baci_85_sample.csv의 결측치 처리[cite: 1]
    baci = baci.dropna() 
    
    # 국가명 매핑 (데이터셋 구조에 맞게 수정 필요: 예시로 수출국 'i', 국가코드 'country_code' 가정)
    if 'i' in baci.columns and 'country_code' in codes.columns:
        df = pd.merge(baci, codes, left_on='i', right_on='country_code', how='left')
        df['country_name'] = df['country_name'].fillna('Unknown')
    else:
        # 테스트용 임시 컬럼 생성 (실제 데이터에 맞춰 변경 필요)
        df = baci.copy()
        df['country_name'] = df['i'] if 'i' in df.columns else 'Unknown'
        
    # 무역액 등급(대, 중, 소) 파생변수 생성 ('v'가 수출액을 의미한다고 가정)
    if 'v' in df.columns:
        q33 = df['v'].quantile(0.33)
        q66 = df['v'].quantile(0.66)
        def assign_grade(val):
            if val <= q33: return '소'
            elif val <= q66: return '중'
            else: return '대'
        df['trade_grade'] = df['v'].apply(assign_grade)
    else:
        df['trade_grade'] = '중' # Fallback
        df['v'] = 1000 # Fallback
        
    # 't' 컬럼이 연도라고 가정
    if 't' not in df.columns:
        df['t'] = 2023 

    return df

df = load_data()

if not df.empty:
    # ------------------- 사이드바: 필터 -------------------
    st.sidebar.header("필터 설정")
    
    # 국가 선택, 무역액 등급 선택(대,중,소) 필터[cite: 1]
    country_list = sorted(df['country_name'].unique().tolist())
    selected_countries = st.sidebar.multiselect("국가 선택", country_list, default=country_list[:5])
    
    grade_list = ['대', '중', '소']
    selected_grades = st.sidebar.multiselect("무역액 등급 선택", grade_list, default=grade_list)
    
    # 필터 적용
    filtered_df = df[
        (df['country_name'].isin(selected_countries)) & 
        (df['trade_grade'].isin(selected_grades))
    ]

    # ------------------- 오른쪽 화면 (메인) -------------------
    
    # 3. 총거래 건수 / 총 수출액(달러)[cite: 1]
    col1, col2 = st.columns(2)
    with col1:
        total_transactions = len(filtered_df)
        st.metric(label="총 거래 건수", value=f"{total_transactions:,} 건")
    with col2:
        total_export_value = filtered_df['v'].sum()
        st.metric(label="총 수출액 (달러)", value=f"${total_export_value:,.2f}")
        
    st.markdown("---")

    # 4. 국가*연도 수출액 히트맵 (상위 8개국) / 무역액 등급분포[cite: 1]
    row1_col1, row1_col2 = st.columns(2)
    
    with row1_col1:
        st.subheader("국가별/연도별 수출액 히트맵 (상위 8개국)")
        # 상위 8개국 추출
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
        grade_dist = filtered_df['trade_grade'].value_counts().reset_index()
        grade_dist.columns = ['무역액 등급', '건수']
        fig_pie = px.pie(
            grade_dist, names='무역액 등급', values='건수',
            color='무역액 등급', color_discrete_map={'대':'#EF553B', '중':'#636EFA', '소':'#00CC96'}
        )
        st.plotly_chart(fig_pie, use_container_width=True)
        
    st.markdown("---")

    # 5. 상위 5개국 * 무역액 등급 교차표 (원본건수 / 정규화비율)[cite: 1]
    st.subheader("상위 5개국 무역액 등급 교차표")
    
    # 상위 5개국 추출
    top_5_countries = df.groupby('country_name')['v'].sum().nlargest(5).index
    cross_df = df[df['country_name'].isin(top_5_countries)]
    
    row2_col1, row2_col2 = st.columns(2)
    
    with row2_col1:
        st.markdown("**원본 건수**")
        crosstab_raw = pd.crosstab(cross_df['country_name'], cross_df['trade_grade'])
        # 등급 순서 정렬
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
        # 소수점 2자리 포맷팅
        st.dataframe(crosstab_norm.style.format("{:.2f}%"), use_container_width=True)