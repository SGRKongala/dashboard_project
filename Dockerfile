FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x start_apps.sh

# Expose both ports
EXPOSE 8080
EXPOSE 8052

CMD ["./start_apps.sh"]