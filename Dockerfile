FROM python:3.6-alpine

#create login with no password
RUN adduser -D melly

WORKDIR /home/melly

COPY requirements.txt requirements.txt

# for pyzmqt
#RUN apk add build-base libzmq python3 zeromq-dev

# for lxml
RUN apk add g++ libxslt-dev
# RUN apk add libxml2-dev libxslt1-dev

RUN python -m venv venv
RUN venv/bin/pip install --upgrade pip
RUN venv/bin/pip install -r requirements.txt
RUN venv/bin/pip install gunicorn pymysql

COPY app app
COPY migrations migrations
COPY melly.py config.py boot.sh ./
RUN chmod +x boot.sh

ENV FLASK_APP melly.py

RUN chown -R melly:melly ./
USER melly

EXPOSE 5000
ENTRYPOINT ["./boot.sh"]