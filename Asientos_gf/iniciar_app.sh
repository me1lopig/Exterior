#!/usr/bin/env sh
set -eu
python -m pip install -r requirements.txt
python -m streamlit run app.py
