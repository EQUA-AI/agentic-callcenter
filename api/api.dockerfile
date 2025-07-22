FROM python:3.12-slim

# Step 1 - Install dependencies
WORKDIR /app

# Step 2 - Copy only requirements.txt
COPY requirements.txt /app

# Step 3 - Install pip dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Step 4 - Copy the rest of the files
COPY . .
ENV PYTHONUNBUFFERED=1

# Expose the application port
EXPOSE 80
WORKDIR /app

# do not change the arguments
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "80"]