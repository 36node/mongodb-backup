FROM mongo:4.4.10
LABEL org.opencontainers.image.authors="cc3630test@gmail.com"

RUN wget -qO - https://www.mongodb.org/static/pgp/server-4.4.asc | sudo apt-key add - \
  echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/4.4 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-4.4.list

RUN apt-get update && \
  apt-get install -y zip psmisc python3

WORKDIR /app
ADD . /app

VOLUME /backup

RUN chmod 777 /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
