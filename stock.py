#!/usr/bin/python
# -*- coding:utf-8 -*-
from PIL import Image, ImageFont, ImageDraw
import requests
import sys
import time
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DEBUG = "--debug" in sys.argv

if not DEBUG:
    from waveshare_epd import epd2in13_V3

SYMBOL = "TSLA"

TIMEZONE = "Asia/Kuala_Lumpur"

API_KEY = os.getenv("TWELVEDATA_API_KEY")

API_URL = f"https://api.twelvedata.com/time_series?apikey={API_KEY}&symbol={SYMBOL}&interval=1min&timezone={TIMEZONE}"

# Display dimensions (landscape)
DISPLAY_WIDTH = 250
DISPLAY_HEIGHT = 122

# Left section width (~1/3 of display)
LEFT_WIDTH = 83


def fetch_stock_data():
    response = requests.get(API_URL)
    data = response.json()

    if data.get("status") != "ok":
        raise Exception(f"API error: {data}")

    values = data["values"]
    meta = data["meta"]

    latest = values[0]
    previous = values[1]

    symbol = meta["symbol"]
    latest_datetime = latest["datetime"]
    latest_price = float(latest["close"])
    previous_price = float(previous["close"])

    pct_change = ((latest_price - previous_price) / previous_price) * 100

    return {
        "symbol": symbol,
        "datetime": latest_datetime,
        "price": latest_price,
        "pct_change": pct_change,
    }


def calculate_optimal_font_size(draw, text, font_path, max_width, min_size=10, max_size=50):
    """Calculate the optimal font size to fit text within max_width"""
    for size in range(max_size, min_size - 1, -1):
        font = ImageFont.truetype(font_path, size=size)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        if text_width <= max_width:
            return font, size
    return ImageFont.truetype(font_path, size=min_size), min_size


def update_display():
    stock = fetch_stock_data()

    canvas = Image.new("1", (DISPLAY_WIDTH, DISPLAY_HEIGHT), 255)
    draw = ImageDraw.Draw(canvas)

    # --- Left section: black background with white ticker ---
    draw.rectangle([(0, 0), (LEFT_WIDTH, DISPLAY_HEIGHT)], fill=0)

    fontBold28 = ImageFont.truetype("Inter_28pt-Bold.ttf", size=28)
    ticker = stock["symbol"].upper()

    # Center the ticker vertically and horizontally in the left section
    ticker_bbox = draw.textbbox((0, 0), ticker, font=fontBold28)
    ticker_w = ticker_bbox[2] - ticker_bbox[0]
    ticker_h = ticker_bbox[3] - ticker_bbox[1]
    ticker_x = (LEFT_WIDTH - ticker_w) // 2 - ticker_bbox[0]
    ticker_y = (DISPLAY_HEIGHT - ticker_h) // 2 - ticker_bbox[1]

    draw.text((ticker_x, ticker_y), ticker, font=fontBold28, fill=255)

    # --- Right section: stock info ---
    right_x = LEFT_WIDTH + 10
    right_w = DISPLAY_WIDTH - LEFT_WIDTH - 10

    fontMedium10 = ImageFont.truetype("Inter_28pt-Medium.ttf", size=10)
    fontSemiBold14 = ImageFont.truetype("Inter_28pt-SemiBold.ttf", size=14)

    # Line 1: Date and time (formatted)
    dt_obj = datetime.strptime(stock["datetime"], "%Y-%m-%d %H:%M:%S")
    dt_str = dt_obj.strftime("%b %d, %Y %I:%M %p")
    draw.text((right_x, 14), dt_str, font=fontMedium10, fill=0)

    # Line 2: Latest price (bold, big) - dynamically sized to fill width
    price_str = f"${stock['price']:.2f}"
    fontBold_price, price_font_size = calculate_optimal_font_size(
        draw, price_str, "Inter_28pt-Bold.ttf", right_w - 10, min_size=18, max_size=40
    )
    price_y = 32
    draw.text((right_x, price_y), price_str, font=fontBold_price, fill=0)

    # Calculate the height of the price text for positioning the next line
    price_bbox = draw.textbbox(
        (right_x, price_y), price_str, font=fontBold_price)
    price_bottom = price_bbox[3]

    # Line 3: Percentage change - positioned below price with margin
    pct = stock["pct_change"]
    if pct >= 0:
        pct_str = f"+{pct:.4f}%"
    else:
        pct_str = f"{pct:.4f}%"

    # Add a triangle indicator
    indicator = "▲ " if pct >= 0 else "▼ "
    pct_y = price_bottom + 8  # 8px margin below price text
    draw.text((right_x, pct_y), indicator +
              pct_str, font=fontSemiBold14, fill=0)

    if DEBUG:
        canvas.save("stock_debug.png")
        print("Debug image saved to stock_debug.png")
    else:
        epd = epd2in13_V3.EPD()
        epd.init()
        epd.Clear(0xFF)
        epd.display(epd.getbuffer(canvas))
        epd.sleep()


while True:
    try:
        update_display()
    except Exception as e:
        print(f"Error: {e}")
    time.sleep(60 * 2)
