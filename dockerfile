# Use an official lightweight Python image
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Copy project files to the container
COPY . /app

RUN pip install --upgrade pip
RUN apt-get update && apt-get install -y build-essential gcc
RUN pip install --upgrade pip && pip install -r requirements.txt
# Expose Flask default port
EXPOSE 5000

# Command to run the app
CMD ["python", "app.py"]
