FROM python:3.7

RUN apt-get update
RUN apt-get install ffmpeg libsm6 libxext6  -y

WORKDIR /usr/src/app

COPY ./webapp/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "webapp.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
