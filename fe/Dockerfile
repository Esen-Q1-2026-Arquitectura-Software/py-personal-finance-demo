FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Flask docs: https://flask.palletsprojects.com/en/3.0.x/deploying/
ENV FLASK_APP=app.py
ENV FLASK_ENV=development

CMD ["flask", "run", "--host=0.0.0.0", "--port=5000", "--debug"]
