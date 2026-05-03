#!/bin/bash
echo "Starting Streamlit UI on PORT $PORT..."
streamlit run bot/ui/app.py --server.port=$PORT --server.address=0.0.0.0
