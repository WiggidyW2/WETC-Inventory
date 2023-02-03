FROM alpine:3.15

LABEL maintainer="wiggidy" mail="wiggidy@riseup.net"
LABEL description="Python script that scrapes ESI for corp asset information and updates a Google Spreadsheet with said assets"

RUN apk add --no-cache \
    python3 \
    py3-pip \
 && pip3 install --no-cache-dir \
    gspread \
    esipy

COPY ./db.py /
COPY ./esi.py /
COPY ./main.py /
COPY ./type_info.csv /

RUN chmod +x /main.py

CMD ["/main.py"]