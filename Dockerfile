FROM tiangolo/uvicorn-gunicorn-fastapi:python3.9

WORKDIR /usr/src/app

COPY requirements.txt .
RUN pip3 install -r requirements.txt
COPY . .

EXPOSE 8000
