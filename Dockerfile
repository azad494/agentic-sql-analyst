# 1. Use an official, lightweight, isolated Python base build image
FROM python:3.12-slim

# 2. Set up a secure internal directory workspace inside the container
WORKDIR /app

# 3. Pre-install crucial OS-level system utilities required for compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 4. Copy ONLY requirements.txt first to maximize layer compilation caching performance
COPY requirements.txt .

# 5. Compile and install your dependencies cleanly within the sealed sandbox env
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 6. Copy the rest of your application files into the active image container
COPY . .

# 7. Expose Streamlit's default network routing interface port
EXPOSE 8501

# 8. Configure a service container health check to monitor live stability 
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# 9. Direct Docker to boot your web app cleanly, routing outward on port 8501
# Force an explicit exec JSON array execution form to capture OS signals and lock port streaming open
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]