#!/bin/bash

echo "======================================"
echo "Running New ETL Modules and Miners"
echo "======================================"

echo ""
echo "[1/5] Running DEV Community ETL..."
python src/etl/news/news_get_devto.py
if [ $? -ne 0 ]; then
    echo "ERROR: DEV Community ETL failed"
    exit 1
fi

echo ""
echo "[2/5] Running Product Hunt ETL..."
python src/etl/news/news_get_producthunt.py
if [ $? -ne 0 ]; then
    echo "ERROR: Product Hunt ETL failed"
    exit 1
fi

echo ""
echo "[3/5] Running Indie Hackers ETL..."
python src/etl/news/news_get_indiehackers.py
if [ $? -ne 0 ]; then
    echo "ERROR: Indie Hackers ETL failed"
    exit 1
fi

echo ""
echo "[4/5] Running Lobsters ETL..."
python src/etl/news/news_get_lobsters.py
if [ $? -ne 0 ]; then
    echo "ERROR: Lobsters ETL failed"
    exit 1
fi

echo ""
echo "[5/5] Running Crypto Sentiment Miner..."
python src/miners/crypto_sentiment_miner.py
if [ $? -ne 0 ]; then
    echo "ERROR: Crypto Sentiment Miner failed"
    exit 1
fi

echo ""
echo "======================================"
echo "All ETL modules completed successfully!"
echo "======================================"
echo ""
echo "Data has been saved to:"
echo "- data/dev_community/"
echo "- data/product_hunt/"
echo "- data/indie_hackers/"
echo "- data/lobsters/"
echo "- data/crypto_sentiment/"
echo "" 