import streamlit as st
import json
import pandas as pd
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import plotly.graph_objects as go



# Set up the page layout
st.set_page_config(
    page_title="State and Lake Chicago Tavern Reviews",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data
def load_reviews_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)


@st.cache_data
def load_reviews_csv(file_path):
    return pd.read_csv(file_path)


def convert_review_date(date_str):
    """Convert mixed date strings like 'Dined 2 days ago' and 'Dined on ...' to datetime."""
    if 'days ago' in date_str:
        days_ago = int(date_str.split()[1])
        return datetime.now() - timedelta(days=days_ago)
    if 'Dined on' in date_str:
        return pd.to_datetime(date_str.replace('Dined on ', ''), format='%B %d, %Y')
    return pd.to_datetime(date_str, format="%Y-%m-%d")


def build_review_search_index(reviews_data):
    """Build a searchable lowercase text index for reviews."""
    return [json.dumps(review).lower() for review in reviews_data]


def compute_yearly_rating_data(csv_file_path):
    """Pure yearly rating calculation used for caching and background warming."""
    df = pd.read_csv(csv_file_path)
    review_dates = df["Date of Review"].apply(convert_review_date)
    ratings = df["Rating"].apply(lambda x: int(x.split()[0]))
    resampled = pd.DataFrame({'Date': review_dates, 'Rating': ratings})
    try:
        return resampled.resample('Y', on='Date').mean()
    except ValueError:
        return resampled.resample('A-DEC', on='Date').mean()


def compute_overall_review_summary(csv_file_path, restaurant_name):
    """Pure KPI summary calculation used for caching and background warming."""
    df = pd.read_csv(csv_file_path)
    avg_rating = df['Rating'].apply(lambda x: int(x.split()[0])).mean()
    total_reviews = len(df)
    positive_reviews = df[df['Rating'].str.contains('5 stars')].shape[0]
    negative_reviews = df[df['Rating'].str.contains('1 star')].shape[0]

    return {
        "restaurant_name": restaurant_name,
        "avg_rating": avg_rating,
        "total_reviews": total_reviews,
        "positive_reviews": positive_reviews,
        "negative_reviews": negative_reviews
    }


@st.cache_data
def get_yearly_rating_data(csv_file_path):
    """Precompute yearly average rating series for a restaurant CSV."""
    return compute_yearly_rating_data(csv_file_path)


@st.cache_data
def overall_review_summary(csv_file_path, restaurant_name):
    """Compute top-level KPI metrics for the overall summary section."""
    return compute_overall_review_summary(csv_file_path, restaurant_name)


@st.cache_data
def get_review_search_index(reviews_data):
    """Cache the searchable review corpus for fast filtering."""
    return build_review_search_index(reviews_data)


def initialize_background_analysis(reviews_data):
    """Kick off background analysis so it continues across page switches in the same session."""
    if 'analysis_executor' not in st.session_state:
        st.session_state.analysis_executor = ThreadPoolExecutor(max_workers=4)

    if 'analysis_futures' not in st.session_state:
        executor = st.session_state.analysis_executor
        st.session_state.analysis_futures = {
            'review_search_index': executor.submit(build_review_search_index, reviews_data),
            'state_yearly': executor.submit(compute_yearly_rating_data, 'state_and_lake_chicago_tavern_reviews.csv'),
            'second_yearly': executor.submit(compute_yearly_rating_data, 'second_restaurant_reviews.csv'),
            'state_summary': executor.submit(compute_overall_review_summary, 'state_and_lake_chicago_tavern_reviews.csv', 'State and Lake Chicago Tavern'),
            'second_summary': executor.submit(compute_overall_review_summary, 'second_restaurant_reviews.csv', 'Heirloom - New Haven'),
        }


def get_background_result(future_key, fallback_func, *args):
    """Return completed background results when available, otherwise use the cached fallback."""
    future = st.session_state.get('analysis_futures', {}).get(future_key)
    if future is not None and future.done():
        try:
            return future.result()
        except Exception:
            pass
    return fallback_func(*args)


def get_analysis_status():
    futures = st.session_state.get('analysis_futures', {})
    if not futures:
        return "ready"
    return "ready" if all(future.done() for future in futures.values()) else "warming"


# Load the reviews data from the JSON file
reviews = load_reviews_json('claude_response.json')
initialize_background_analysis(reviews)

# Custom CSS for the entire app
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;700&family=Playfair+Display:wght@500;600;700&display=swap');

    :root {
        --bg-1: #111111;
        --bg-2: #1a1714;
        --ink: #f6f0e8;
        --muted: #d0c3b2;
        --brand: #b08a4a;
        --brand-2: #d8bf8f;
        --card: rgba(255, 248, 236, 0.08);
        --line: rgba(216, 191, 143, 0.30);
        --shadow: rgba(0, 0, 0, 0.40);
    }

    .stApp {
        color: var(--ink);
        font-family: 'Manrope', sans-serif;
        background: radial-gradient(circle at 12% 16%, rgba(176, 138, 74, 0.20) 0%, transparent 28%),
                    radial-gradient(circle at 88% 8%, rgba(255, 223, 165, 0.15) 0%, transparent 26%),
                    linear-gradient(140deg, var(--bg-1), #15110f 45%, var(--bg-2));
        animation: bgShift 20s ease-in-out infinite alternate;
    }

    @keyframes bgShift {
        0% { background-position: 0% 0%, 100% 0%, 50% 50%; }
        100% { background-position: 6% 6%, 94% 4%, 45% 55%; }
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #171310 0%, #0f0c0a 100%);
        border-right: 1px solid rgba(216, 191, 143, 0.25);
    }

    [data-testid="stSidebar"] * {
        color: #f4ede3;
        font-family: 'Manrope', sans-serif;
    }

    .stRadio > div {
        gap: 0.5rem;
    }

    .stRadio > div > label {
        background: rgba(216, 191, 143, 0.07);
        border: 1px solid rgba(216, 191, 143, 0.24);
        border-radius: 10px;
        padding: 10px 12px;
        transition: all 0.25s ease;
    }

    .stRadio > div > label:hover {
        background: rgba(216, 191, 143, 0.20);
        transform: translateX(4px);
    }

    .stButton>button, .stDownloadButton>button {
        background: linear-gradient(90deg, #8e6f3b, var(--brand-2));
        color: #1a130b;
        padding: 10px 20px;
        border: none;
        border-radius: 999px;
        cursor: pointer;
        font-family: 'Manrope', sans-serif;
        font-weight: 700;
        transition: transform 0.25s ease, box-shadow 0.25s ease, filter 0.25s ease;
        box-shadow: 0 10px 24px rgba(176, 138, 74, 0.34);
    }

    .stButton>button:hover, .stDownloadButton>button:hover {
        transform: translateY(-2px);
        filter: brightness(1.05);
    }

    .heading {
        font-size: clamp(2.1rem, 6vw, 3.8rem);
        color: var(--ink);
        font-family: 'Playfair Display', serif;
        font-weight: 700;
        letter-spacing: 0.03em;
        text-align: center;
        margin-top: 0.3rem;
        margin-bottom: 0.6rem;
        animation: fadeSlide 0.75s ease both;
    }

    .subheading {
        text-align: center;
        color: var(--muted);
        font-size: 1.02rem;
        margin-bottom: 1.2rem;
    }

    @keyframes fadeSlide {
        from { transform: translateY(8px); opacity: 0; }
        to { transform: translateY(0); opacity: 1; }
    }

    .feature-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 12px;
        margin: 1rem 0 1.6rem;
    }

    .feature-tile {
        background: var(--card);
        border: 1px solid var(--line);
        border-radius: 16px;
        backdrop-filter: blur(6px);
        -webkit-backdrop-filter: blur(6px);
        padding: 0.9rem;
        animation: fadeSlide 0.7s ease both;
        box-shadow: 0 8px 24px var(--shadow);
    }

    .feature-tile strong {
        display: block;
        margin-top: 0.3rem;
        color: var(--ink);
        font-family: 'Playfair Display', serif;
        font-size: 1.2rem;
    }

    .features-list {
        font-family: 'Manrope', sans-serif;
        font-size: 1.03rem;
        padding: 0;
    }

    .feature-item {
        display: block;
        margin: 8px 0;
        color: var(--muted);
    }

    .highlight {
        color: #d5b67a;
    }

    .highlight-blue {
        color: #ecd8b5;
    }

    .btn-container {
        margin-top: 24px;
        text-align: center;
    }

    .review-card {
        background: var(--card);
        border: 1px solid var(--line);
        border-radius: 18px;
        padding: 18px 18px 10px 18px;
        margin: 14px 0;
        box-shadow: 0 14px 34px var(--shadow);
        transition: transform 0.28s ease, box-shadow 0.28s ease;
        animation: fadeSlide 0.6s ease both;
    }

    .review-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 18px 40px rgba(0, 0, 0, 0.56);
    }

    .review-heading {
        font-size: 1.6em;
        color: #f1dec1;
        font-weight: bold;
        margin-bottom: 10px;
        text-align: center;
        font-family: 'Playfair Display', serif;
    }

    .review-content {
        font-size: 1.04rem;
        color: var(--ink);
        margin-bottom: 10px;
    }

    .review-highlight-food {
        color: #e6c992;
        font-weight: bold;
    }

    .review-highlight-service {
        color: var(--brand-2);
        font-weight: bold;
    }

    .rating-stars {
        color: #e6c47e;
        font-size: 1.3em;
        margin-top: 5px;
        text-align: center;
    }

    .key {
        font-weight: bold;
        color: #f0d6a6;
    }

    .value {
        color: #d9cbb9;
    }

    .no-data {
        color: #c0b3a5;
        font-style: italic;
    }

    .section-panel {
        background: var(--card);
        border: 1px solid var(--line);
        border-radius: 18px;
        padding: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 14px 34px var(--shadow);
    }

    .section-title {
        font-family: 'Playfair Display', serif;
        font-size: 2rem;
        color: var(--ink);
        text-align: center;
        margin: 0.2rem 0 0.4rem;
    }

    [data-testid="stMetric"] {
        background: rgba(255, 244, 227, 0.10);
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 10px;
    }

    [data-testid="stMetricLabel"], [data-testid="stMetricValue"] {
        color: #f4e7d2;
    }

    [data-testid="stDataFrame"] {
        border: 1px solid var(--line);
        border-radius: 14px;
        overflow: hidden;
        background: rgba(255, 255, 255, 0.03);
    }

    footer {
        text-align: center;
        margin-top: 30px;
        color: #d9cab5;
        font-size: 0.92rem;
    }

    @media (max-width: 720px) {
        .review-card {
            padding: 14px 12px 8px 12px;
        }
        .features-list {
            font-size: 0.95rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Sidebar for navigation
st.sidebar.title("Navigation")
st.sidebar.markdown("Choose an option to explore:")
st.sidebar.caption(f"Analysis engine: {get_analysis_status()}")

# Sidebar options
options = ["Splash Screen", "Dashboard", "Data Table", "Comparison Charts","Overall Summary"]
if 'selection' not in st.session_state:
    st.session_state.selection = "Splash Screen"


def go_to_dashboard():
    st.session_state.selection = "Dashboard"


selection = st.sidebar.radio("Go to", options, key='selection')

# Splash Screen Section
if selection == "Splash Screen":
    def splash_screen():
        st.markdown(
            """
            <h1 class="heading">State and Lake Review Observatory</h1>
            <p class="subheading">A dynamic lens on food quality, service behavior, and customer sentiment.</p>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            """
            <div class="feature-grid">
                <div class="feature-tile">🔍 <strong>Precision Search</strong><span class="feature-item">Filter deeply through structured review fields.</span></div>
                <div class="feature-tile">🍽️ <strong>Food vs Service</strong><span class="feature-item">Separate praise and pain points instantly.</span></div>
                <div class="feature-tile">📈 <strong>Trend Radar</strong><span class="feature-item">Compare long-term rating movement by restaurant.</span></div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.button('Go to Dashboard', on_click=go_to_dashboard)
    splash_screen()

elif selection == "Dashboard":
    def extract_numeric_rating(rating_str):
        match = re.search(r'\d+', str(rating_str))
        return int(match.group()) if match else 0

    def format_nested_data(data):
        """Recursively formats nested data into HTML-friendly content."""
        if isinstance(data, dict):
            return "<ul>" + "".join(f"<li><b style='color: #f39c12;'>{key.capitalize()}</b>: {format_nested_data(value)}</li>" for key, value in data.items()) + "</ul>"
        elif isinstance(data, list):
            return "<ul>" + "".join(f"<li>{format_nested_data(item)}</li>" for item in data) + "</ul>"
        else:
            return str(data)

    def dashboard(reviews):
        st.markdown("<div class='section-panel'><h2 class='section-title'>Live Review Dashboard</h2></div>", unsafe_allow_html=True)

        search_query = st.text_input(
            'Search for reviews',
            placeholder='Enter keywords to search reviews...',
            help='Type keywords to filter reviews',
            key='dashboard_search_query',
        )

        search_index = get_background_result('review_search_index', get_review_search_index, reviews)

        filtered_reviews = [
            review for review, search_blob in zip(reviews, search_index)
            if search_query.lower() in search_blob
        ] if search_query else reviews

        if not filtered_reviews:
            st.warning("No reviews match your search criteria.")
        else:
            st.markdown(f"<p style='color: #d7c7b0;'>Displaying <b>{len(filtered_reviews)}</b> result(s) for query: <i>{search_query}</i></p>", unsafe_allow_html=True)

        for review in filtered_reviews:
            with st.container():
                st.markdown("<div class='review-card'>", unsafe_allow_html=True)
                review_name = review.get('name', 'Anonymous')
                dining_time = review.get('dining_time', 'Unknown Date')
                rating = extract_numeric_rating(review.get('rating', 0))

                st.markdown(f"<h3 class='review-heading'>{review_name}</h3>", unsafe_allow_html=True)
                st.markdown(f"<p style='color: #d0bfaa; text-align:center; margin-bottom:4px;'>{dining_time}</p>", unsafe_allow_html=True)

                stars = "★" * rating + "☆" * (5 - rating)
                st.markdown(f"<p class='rating-stars'>{stars}</p>", unsafe_allow_html=True)

                food_quality = review.get('food_quality', 'No food quality provided')
                st.markdown("<h4 style='color:#f1d8ab; margin-bottom:4px;'>Food Quality</h4>", unsafe_allow_html=True)
                st.markdown(format_nested_data(food_quality), unsafe_allow_html=True)

                staff_service = review.get('staff_service', 'No staff service provided')
                st.markdown("<h4 style='color:#e6d4b0; margin-bottom:4px;'>Staff Service</h4>", unsafe_allow_html=True)
                st.markdown(format_nested_data(staff_service), unsafe_allow_html=True)

                other_comments = review.get('comments', [])
                if other_comments:
                    st.markdown("<h4 style='color:#d9c09d; margin-bottom:4px;'>Other Comments</h4>", unsafe_allow_html=True)
                    st.markdown(format_nested_data(other_comments), unsafe_allow_html=True)

                st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<footer style='text-align:center; padding: 10px;'>Powered by <b>Streamlit</b> | Designed by Hamda Shahid</footer>", unsafe_allow_html=True)

    dashboard(reviews)

# Data Table Section
elif selection == "Data Table":
    st.markdown("<div class='section-panel'><h2 class='section-title'>Data Explorer</h2></div>", unsafe_allow_html=True)

    # Load the data from the CSV files
    csv_file1 = 'state_and_lake_chicago_tavern_reviews.csv'
    csv_file2 = 'second_restaurant_reviews.csv'
    df1 = load_reviews_csv(csv_file1)
    df2 = load_reviews_csv(csv_file2)

    # Display the first data table
    st.subheader("State and Lake Chicago Tavern Reviews")
    st.dataframe(df1)
    st.download_button(
        label="📥 Download State and Lake Data as CSV",
        data=df1.to_csv(index=False),
        file_name="state_and_lake_chicago_tavern_reviews.csv",
        mime="text/csv",
    )

    # Display the second data table
    st.subheader("Heirloom - New Haven Reviews")
    st.dataframe(df2)
    st.download_button(
        label="📥 Download Second Restaurant Data as CSV",
        data=df2.to_csv(index=False),
        file_name="second_restaurant_reviews.csv",
        mime="text/csv",
    )

# # Charts Section
# # Charts Section
# Comparison Charts Section
elif selection == "Comparison Charts":
    # Precompute yearly series once and reuse across reruns
    df1_yearly = get_background_result('state_yearly', get_yearly_rating_data, 'state_and_lake_chicago_tavern_reviews.csv')
    df2_yearly = get_background_result('second_yearly', get_yearly_rating_data, 'second_restaurant_reviews.csv')

    # Compute safe slider bounds from both datasets
    year_min = int(min(df1_yearly.index.year.min(), df2_yearly.index.year.min()))
    year_max = int(max(df1_yearly.index.year.max(), df2_yearly.index.year.max()))
    default_start = max(year_min, year_max - 10)

    # Define custom year ranges and dynamic filters
    st.sidebar.header("Filter Data")
    min_year, max_year = st.sidebar.slider(
        "Select Year Range:", 
        min_value=year_min,
        max_value=year_max,
        value=(default_start, year_max),
        step=1,
        key='comparison_year_range'
    )

    # Filter data based on user-selected year range
    df1_yearly = df1_yearly[(df1_yearly.index.year >= min_year) & (df1_yearly.index.year <= max_year)]
    df2_yearly = df2_yearly[(df2_yearly.index.year >= min_year) & (df2_yearly.index.year <= max_year)]

    # Plot for Restaurant 1
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(
        x=df1_yearly.index,
        y=df1_yearly['Rating'],
        mode='lines+markers',
        name='Restaurant 1',
        line=dict(shape='linear', width=2, color='#636EFA'),
        marker=dict(size=8, color='#636EFA')
    ))
    fig1.update_layout(
        title='Rating Trends for State and Lake Chicago Tavern',
        xaxis_title='Year',
        yaxis_title='Average Rating',
        xaxis=dict(showgrid=True, tickangle=45, gridcolor='rgba(216,191,143,0.18)', color='#efe1cd'),
        yaxis=dict(showgrid=True, gridcolor='rgba(216,191,143,0.18)', color='#efe1cd'),
        template='plotly_dark',
        font=dict(size=14),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(22,18,15,0.7)',
        title_font=dict(size=18)
    )
    st.plotly_chart(fig1, use_container_width=True)

    # Plot for Restaurant 2
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=df2_yearly.index,
        y=df2_yearly['Rating'],
        mode='lines+markers',
        name='Restaurant 2',
        line=dict(shape='linear', dash='dash', width=2, color='#EF553B'),
        marker=dict(size=8, symbol='x', color='#EF553B')
    ))
    fig2.update_layout(
        title='Rating Trends for Heirloom - New Haven',
        xaxis_title='Year',
        yaxis_title='Average Rating',
        xaxis=dict(showgrid=True, tickangle=45, gridcolor='rgba(216,191,143,0.18)', color='#efe1cd'),
        yaxis=dict(showgrid=True, gridcolor='rgba(216,191,143,0.18)', color='#efe1cd'),
        template='plotly_dark',
        font=dict(size=14),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(22,18,15,0.7)',
        title_font=dict(size=18)
    )
    st.plotly_chart(fig2, use_container_width=True)

    # Comparison Plot
    fig = go.Figure()

    # Add traces for both restaurants
    fig.add_trace(go.Scatter(
        x=df1_yearly.index,
        y=df1_yearly['Rating'],
        mode='lines+markers',
        name='State and Lake Chicago Tavern',
        line=dict(shape='linear', width=2, color='#636EFA'),
        marker=dict(size=8, color='#636EFA')
    ))

    fig.add_trace(go.Scatter(
        x=df2_yearly.index,
        y=df2_yearly['Rating'],
        mode='lines+markers',
        name='Heirloom - New Haven',
        line=dict(shape='linear', dash='dash', width=2, color='#EF553B'),
        marker=dict(size=8, symbol='x', color='#EF553B')
    ))

    # Highlight peak ratings with annotations
    if not df1_yearly.empty:
        max_rating_1 = df1_yearly['Rating'].max()
        peak_year_1 = df1_yearly['Rating'].idxmax()
        fig.add_annotation(
            x=peak_year_1,
            y=max_rating_1,
            text=f"Peak: {max_rating_1:.1f}",
            showarrow=True,
            arrowhead=1,
            arrowcolor="black",
            bgcolor="blue",
            font=dict(color="white")
        )

    if not df2_yearly.empty:
        max_rating_2 = df2_yearly['Rating'].max()
        peak_year_2 = df2_yearly['Rating'].idxmax()
        fig.add_annotation(
            x=peak_year_2,
            y=max_rating_2,
            text=f"Peak: {max_rating_2:.1f}",
            showarrow=True,
            arrowhead=1,
            arrowcolor="black",
            bgcolor="red",
            font=dict(color="white")
        )

    # Update layout for better visual appeal
    fig.update_layout(
        title='Rating Comparison Trends for State and Lake Restaurant and Heirloom - New Haven Restaurant',
        xaxis_title='Year',
        yaxis_title='Average Rating',
        xaxis=dict(showgrid=True, tickangle=45, gridcolor='rgba(216,191,143,0.18)', color='#efe1cd'),
        yaxis=dict(showgrid=True, gridcolor='rgba(216,191,143,0.18)', color='#efe1cd'),
        legend_title='Restaurant',
        template='plotly_dark',
        font=dict(size=14),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(22,18,15,0.7)',
        title_font=dict(size=18),
        hovermode='x unified'
    )

    # Display the comparison plot in Streamlit
    st.plotly_chart(fig, use_container_width=True)

elif selection == "Overall Summary":
    # Overall Summary Section
    st.markdown("<div class='section-panel'><h2 class='section-title'>Overall Review Summary</h2></div>", unsafe_allow_html=True)
    
    # Summarize reviews for both restaurants
    summary1 = get_background_result('state_summary', overall_review_summary, 'state_and_lake_chicago_tavern_reviews.csv', "State and Lake Chicago Tavern")
    summary2 = get_background_result('second_summary', overall_review_summary, 'second_restaurant_reviews.csv', "Heirloom - New Haven")

    # Define a helper function to display styled metrics
    def display_summary(summary):
        st.subheader(f"🍴 {summary['restaurant_name']}")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("🌟 Average Rating", f"{summary['avg_rating']:.2f} stars")
        with col2:
            st.metric("📝 Total Reviews", summary["total_reviews"])
        with col3:
            st.metric("😊 Positive Reviews", summary["positive_reviews"])
        
        col4, col5 = st.columns(2)
        with col4:
            st.metric("☹️ Negative Reviews", summary["negative_reviews"])
        with col5:
            pos_percentage = (summary["positive_reviews"] / summary["total_reviews"]) * 100
            st.metric("📊 Positive Review %", f"{pos_percentage:.1f}%")

    # Display summaries with an attractive layout
    st.markdown("### 🏆 Review Summaries")
    with st.container():
        st.write("---")  # Separator for better layout
        display_summary(summary1)
        st.write(" ")
        st.write(" ")
        st.write(" ")
        display_summary(summary2)
    
    # Add an interactive component (e.g., download button)
    st.download_button(
        label="📥 Download Summary",
        data=f"Summary for State and Lake Chicago Tavern:\n{summary1}\n\nSummary for Heirloom - New Haven:\n{summary2}",
        file_name="overall_review_summary.txt",
        mime="text/plain"
    )
    