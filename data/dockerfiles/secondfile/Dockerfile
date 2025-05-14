# Use an official Python base image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port (optional, for web apps)
EXPOSE 8000

# Run the application (change this according to your app)
CMD ["python", "app.py"]