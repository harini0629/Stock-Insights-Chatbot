import streamlit as st
import requests
import base64

# FastAPI Endpoint for the summary from mistral AI
API_URL_SUMMARY = "http://127.0.0.1:8080/summary"

# Streamlit Page Config
st.set_page_config(page_title="Stock Insights Chatbot", layout="wide")

# Sidebar for User Inputs
with st.sidebar:
    st.header(" Stock Information")
    symbol = st.text_input("Enter Stock Symbol", "AAPL")
    timeframe = st.selectbox("Select Timeframe", ["1mo", "3mo", "6mo", "1y", "5y"])

st.title(" Stock Insights Chatbot")
st.markdown("Get real-time stock data, trends, AI insights, and news in one place.")

# Maintain chat history
if "history" not in st.session_state:
    st.session_state.history = []

# Chat Input
user_message = st.text_input("Ask about the stock:")

#  Handle API Request
if st.button("Get Insights"):
    if user_message:
        payload = {"symbol": symbol, "timeframe": timeframe, "user_message": user_message}
        response = requests.post(API_URL_SUMMARY, json=payload)

        if response.status_code == 200:
            data = response.json()

            #  Store user question & AI response
            st.session_state.history.append(("You", user_message))
            st.session_state.history.append(("Bot", data.get("ai_summary", "No AI response")))

            #  Display stock details in a clear format
            st.subheader(f" Stock Data for {symbol}")
            st.write(f"**Current Price:** ${data.get('real_time_price', 'N/A')}")

            #  Display stock trend plot
            if "trend_plot" in data.get("historical_trend", {}):
                img_data = base64.b64decode(data["historical_trend"]["trend_plot"])
                st.image(img_data, caption=f"{symbol} Stock Trend", use_container_width=True)

            # Display latest news
            st.subheader("Latest News Headlines")
            for news in data.get("latest_news", []):
                st.markdown(f"- {news}")

        else:
            st.error(" API Error! Please try again.")

#  Display chat history
st.subheader(" Chat History")
for role, message in st.session_state.history:
    with st.chat_message(role):
        st.markdown(message)
