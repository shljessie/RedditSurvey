FROM python:3.9

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install the Flask dependencies
RUN pip3 install -r requirements.txt

# Copy the Flask application code
COPY . .

# Expose the Flask application port
EXPOSE 5000

# Start the Flask application
CMD ["python", "app.py"]
