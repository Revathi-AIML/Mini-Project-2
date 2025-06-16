import streamlit as st
import pandas as pd
import plotly.express as px
import mysql.connector
from mysql.connector import Error

st.set_page_config(page_title="Nifty 50 Stock Dashboard", layout="wide")
st.title("Nifty 50 Stock Analysis Dashboard")

def load_data():
    try:
        connection = mysql.connector.connect(
            host = "localhost",
            user = "Revathi",
            password = "Nithisha_6",
            port = 3306,
            database = "MAT4"
        )
        query = "SELECT * FROM stock_data"
        df=pd.read_sql(query,connection)
        df['date'] = pd.to_datetime(df['date'])
        return df
    except Error as e:
        st.error(f"Failed to connect: {e}")
        return pd.DataFrame()
    
df=load_data()

if df.empty:
    st.warning("No Data Available")
    st.stop()

# Year Filter
st.sidebar.header("Filter Options")
df['year'] = df['date'].dt.year
years = sorted(df['year'].unique())
selected_years = st.sidebar.multiselect("Select Year(s)", years, default=years)

# Month Filter
st.sidebar.header("Filter Options")
df['month'] = df['date'].dt.to_period('M').astype(str)
months = sorted(df['month'].unique())
selected_months = st.sidebar.multiselect("Select month(s)", months, default=months)

# Date Filter
min_date = df['date'].min()
max_date = df['date'].max()
selected_date = st.sidebar.date_input("Select Date Range",[min_date,max_date])

# Sector Filter
all_sectors = df['sector'].dropna().unique().tolist()
selected_sectors = st.sidebar.multiselect("Select Sector(s)",all_sectors,default=all_sectors)

top_n = st.sidebar.slider("Select Top N Stocks", min_value=5, max_value=15, value=10)

# Apply filters
filtered_df = df[
    (df['year'].isin(selected_years)) &
    (df['month'].isin(selected_months)) &
    (df['sector'].isin(selected_sectors)) &
    (df["date"] >= pd.to_datetime(selected_date[0])) &
    (df["date"] <= pd.to_datetime(selected_date[1])) 
].copy()

filtered_df['daily_return'] = filtered_df.groupby('Ticker')['close'].pct_change()

st.markdown("---")
st.markdown("Market Summary")

summary_returns = filtered_df.sort_values('date').groupby('Ticker')['close'].agg(['first','last']).reset_index()
summary_returns['status'] = summary_returns.apply(lambda row : 'Green' if row['last'] > row['first'] else 'Red', axis=1)

green_count = (summary_returns['status'] == 'Green').sum()
red_count = (summary_returns['status'] == 'Red').sum()

avg_price = filtered_df['close'].mean()
avg_volume = filtered_df['volume'].mean()

col_summary1, col_summary2, col_summary3 = st.columns(3)
with col_summary1:
    st.metric("Green Stocks : ", green_count)
    st.metric("Red Stocks : ", red_count)
with col_summary2:
    st.metric("Average Close Price : ",f"{avg_price:.2f}")
with col_summary3:
    st.metric("Average volume : ",f"{avg_volume:.0f}")

# Yearly Top Gainers & Losers

st.markdown("---")
st.title("Yearly Top Gainers & Losers")

returns = filtered_df.sort_values('date').groupby('Ticker')['close'].agg(['first', 'last'])
returns['return'] = (returns['last'] / returns['first']) - 1
returns = returns['return'].sort_values(ascending=False)

col1, col2 = st.columns(2)
with col1:
    st.write(f"Top {top_n} Gainers")
    st.dataframe(returns.head(top_n).round(4).reset_index())
with col2:
    st.write(f"Top {top_n} Losers")
    st.dataframe(returns.tail(top_n).round(4).reset_index())

# Volatility

st.markdown("---")
st.title(f"Volatility - Top {top_n} Most Volatile Stocks")

volatility = filtered_df.groupby('Ticker')['daily_return'].std().sort_values(ascending=False).head(top_n).reset_index()
fig_vol = px.bar(volatility, x='Ticker', y='daily_return', title=f'Top {top_n} Most Volatile Stocks')
st.plotly_chart(fig_vol, use_container_width=True)

# Cumulative Return
st.markdown(" ")
st.markdown("---")
st.title(f"Cumulative Return Over Time (Top {top_n})")

top_tickers = returns.head(top_n).index
cum_df = filtered_df[filtered_df['Ticker'].isin(top_tickers)].copy()
cum_df['cumulative_return'] = cum_df.groupby('Ticker')['daily_return'].cumsum()
fig_cum = px.line(cum_df, x='date', y='cumulative_return', color='Ticker', title=f"Cumulative Return (Top {top_n} Stocks)")
st.plotly_chart(fig_cum, use_container_width=True)

# Sector-wise Performance

st.markdown("---")
st.title("Sector-wise Performance")

sector_returns = filtered_df.sort_values('date').groupby('Ticker')['close'].agg(['first', 'last']).reset_index()
sector_returns['yearly_return'] = (sector_returns['last'] / sector_returns['first']) - 1
ticker_sector_map = filtered_df[['Ticker', 'sector']].drop_duplicates()
sector_returns = sector_returns.merge(ticker_sector_map, on='Ticker', how='left')
sector_grouped = sector_returns.groupby('sector')['yearly_return'].mean().reset_index().sort_values(by='yearly_return', ascending=False)
fig_sector = px.bar(sector_grouped, x='sector', y='yearly_return', title='📊 Average Yearly Return by Sector', labels={'yearly_return': 'Avg Return'}, color='sector')
st.plotly_chart(fig_sector, use_container_width=True)

# Correlation Heatmap

st.markdown("---")
st.title("Correlation Heatmap of Daily % Change in Closing Prices")

# Step 1: Pivot table for closing prices
pivot_table = filtered_df.pivot(index='date', columns='Ticker', values='close')

# Step 2: Calculate % daily change
returns_pct = pivot_table.pct_change().dropna() * 100

# Step 3: Correlation matrix
corr_matrix = returns_pct.corr()

# Step 4: Plot correlation heatmap
fig_corr = px.imshow(
    corr_matrix,
    title="Stock Price Correlation Heatmap (Daily % Change)",
    color_continuous_scale='RdBu_r',
    text_auto=".2f",
    width=1200,
    height=700
)
st.plotly_chart(fig_corr, use_container_width=False)


#Monthly Gainers and Losers

st.markdown("---")
st.title("Monthly Gainers and Losers")

monthly = filtered_df.groupby(['month', 'Ticker'])['close'].agg(['first', 'last']).reset_index()
monthly['monthly_return'] = (monthly['last'] / monthly['first']) - 1

if selected_months:
    monthly_selected = monthly[monthly['month'].astype(str) == selected_months[0]]
    top_month = monthly_selected.sort_values('monthly_return', ascending=False).head(top_n)
    bottom_month = monthly_selected.sort_values('monthly_return').head(top_n)

    col3, col4 = st.columns(2)
    with col3:
        fig_top = px.bar(top_month, x='Ticker', y='monthly_return', title=f"Top {top_n} Gainers - {selected_months[0]}")
        st.plotly_chart(fig_top, use_container_width=True)
    with col4:
        fig_bottom = px.bar(bottom_month, x='Ticker', y='monthly_return', title=f"Top {top_n} Losers - {selected_months[0]}")
        st.plotly_chart(fig_bottom, use_container_width=True)

# Footer

st.caption("Data-driven stock analysis using Streamlit & Plotly")