NEWS_API_URL = "https://newsapi.org/v2/everything"
MODEL = "mistralai/Mixtral-8x7B-Instruct-v0.1"

#### Install all packages 
import yfinance as yf ## required to get stock history
import matplotlib ## required to get stock trend
matplotlib.use('Agg')  # Use non-GUI backend for Matplotlib so fast API wont throw an error
import matplotlib.pyplot as plt
import io 
import base64
import re
import requests
from fastapi import FastAPI ## to create api end points
from pydantic import BaseModel ## to make sure user-input has right data types
from huggingface_hub import InferenceClient ## get mistral llm from hugging face cloud
import os
# Retrieve the API key from an environment variable called "API_KEY"
NEWS_API_KEY = os.getenv('NEWS_API_KEY')
Hugging_API_KEY = os.getenv('Hugging_API_KEY')

## initiate list for saving the converstion history
conversation_history = []  

## use this to access the mistral llm from hugging face using the API set up 
client = InferenceClient(model=MODEL, token=API_KEY)

## this creates an instance of FASTAPI application, that acts as a backend server for handling API requests
app = FastAPI()

## We create a pydantic model 
## that takes string input of the stock we want to analyze and time time frame for which we need to analyze trend and user question..
## With Pydantic, FastAPI automatically validates data types:

class StockQuery(BaseModel):
    symbol: str
    timeframe: str = "1y"  # Default to 1 year
    user_message: str  # Fix: Add this field

## create function to get real time stock from Yahoo
def get_realtime_stock(symbol):
    """ Fetch real-time stock price """
    try:
        stock = yf.Ticker(symbol)
        data = stock.history(period="1d")
        price = data['Close'].iloc[-1]
        return {"price": price}
    except Exception as e:
        return {"error": str(e)}
    
## create function to get historic trend time stock from Yahoo and plot it
def get_historical_stock(symbol, timeframe):
    """ Fetch historical stock prices and generate a trend plot """
    try:
        stock = yf.Ticker(symbol)
        data = stock.history(period=timeframe)

        plt.figure(figsize=(10, 5))
        plt.plot(data.index, data['Close'], label=f'{symbol} Price Trend')
        plt.xlabel("Date")
        plt.ylabel("Stock Price")
        plt.title(f"{symbol} Stock Price Trend Over {timeframe}")
        plt.legend()

        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png')
        plt.close()  # Prevent Matplotlib memory leak
        img_buffer.seek(0)
        img_str = base64.b64encode(img_buffer.read()).decode('utf-8')

        return {"trend_plot": img_str, "latest_price": data['Close'].iloc[-1]}
    except Exception as e:
        return {"error": str(e)}

## create a function to get the latest news of the given stock symbol.
def get_stock_news(symbol):
    """ Fetch latest stock news """
    params = {"q": symbol, "sortBy": "publishedAt", "apiKey": NEWS_API_KEY}
    response = requests.get(NEWS_API_URL, params=params)
    
    if response.status_code == 200:
        articles = response.json().get("articles", [])
        top_articles = articles[:5]  # Get top 5 news
        news_summaries = [article['title'] for article in top_articles]
        return news_summaries
    else:
        return {"error": "Failed to fetch news"}

### Takes the user questions and the input from various APIs
### Mistral AI takes all the text, understands the user question and tries to decode 
### the answer question based on the relationship between words 
def chat_with_mistral(user_message, stock_symbol, stock_price):
    """ Generate AI response with conversation context """
    try:
        #  Include conversation history for context
        formatted_history = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history])

        prompt = f"""
        You are a financial analyst providing stock insights.

        Previous Conversation:
        {formatted_history}

        Current Stock: {stock_symbol} priced at ${stock_price}.
        User's Question: {user_message}

        Please analyze the data and provide a meaningful response rather than repeating previous information.
        """
        
        response = client.text_generation(prompt, max_new_tokens=250)
        
        #  Store new conversation message
        conversation_history.append({"role": "User", "content": user_message})
        conversation_history.append({"role": "Bot", "content": response.strip()})

        return response.strip()
    except Exception as e:
        return {"error": str(e)}

## An API end point for summary is created and the service "summary" is ran on back end
## An API endpoint is just a URL where the backend listens for requests.
## Our Client - Stream lit API will call summary API for give summary of the API call.
@app.post("/summary")
def stock_summary(query: StockQuery):
    """ Fetch all stock insights and return a unified summary """
    real_time_data = get_realtime_stock(query.symbol) #gets the stock symbol from user
    historical_data = get_historical_stock(query.symbol, query.timeframe) #gets the time frame from user
    stock_news = get_stock_news(query.symbol) #gets the news about the user given symbol ß

    # Store conversation history
    ## this stores every question user asks and the Chat bot says which can be used as a context for future questions from users
    conversation_history.append({"role": "User", "content": query.user_message})
    conversation_history.append({"role": "Bot", "content": stock_news})

    # Create a prompt, that takes user symbol, price from yahoo finance , time frame from user and also the news from the new API
    # this prompt generate AI insights with context
    
    ai_summary_prompt = f"""
    Stock Symbol: {query.symbol}
    Current Price: {real_time_data.get('price', 'N/A')}
    Historical Trend: {query.timeframe}
    Latest News: {stock_news}
    
    Please generate an AI-powered summary of this data.
    """
    
    ## The above prompt is sent to mistral ai, to summarzie stock price/ news and the trend..
    ai_summary = chat_with_mistral(ai_summary_prompt, query.symbol, real_time_data.get("price", "N/A"))

    return {
        "symbol": query.symbol,
        "real_time_price": real_time_data.get("price", "N/A"),
        "historical_trend": historical_data,
        "latest_news": stock_news,
        "ai_summary": ai_summary,
        "conversation_history": conversation_history  #  Return history
    }

