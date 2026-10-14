FROM python:3.11-slim

WORKDIR /app

# Copy requirements first to leverage caching
COPY requirements.txt .

# --- Install system packages needed for MySQL client libraries ---
RUN apt-get update && \
    apt-get install -y \
        default-mysql-client \
        libmariadb-dev \
        build-essential \
        python3-dev \
        pkg-config \
        iputils-ping \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (including mysqlclient / pymysql)
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --upgrade mysqlclient pymysql \
    && pip install --upgrade pip

# Copy your source code
COPY src/ ./src/
COPY ./.streamlit/config.toml ./ 


# If you still need ping inside the container:
RUN apt-get update && apt-get install -y iputils-ping && rm -rf /var/lib/apt/lists/*

EXPOSE 8050

CMD ["streamlit", "run", "src/graph.py", "--server.port=8050", "--server.address=0.0.0.0"]
