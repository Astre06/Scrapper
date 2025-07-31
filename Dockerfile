FROM python:3.10-alpine

# Set working directory
WORKDIR /app

# Copy all files
COPY . .

# Install system packages for building Python dependencies
RUN apk add --no-cache gcc musl-dev libffi-dev

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run the Telegram bot
CMD ["python", "bot.py"]
