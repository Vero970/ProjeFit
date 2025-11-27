FROM python:3.11-slim
WORKDIR /app
COPY web/requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install --no-cache-dir -r /app/requirements.txt
COPY web /app
EXPOSE 8501
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ENABLE_CORS=false
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
