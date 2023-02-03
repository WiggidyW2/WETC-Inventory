FROM alphine

LABEL maintainer="wiggidy" mail="wiggidy@riseup.net"
LABEL description="Python script that scrapes ESI for corp asset information and updates a Google Spreadsheet with said assets"

ARG GAUTH

RUN apk add --no-cache python3 \
 && pip3 install --no-cache-dir \
    gspread \
    esipy

COPY ./db.py /
COPY ./esi.py /
COPY ./main.py /

RUN chmod +x /main.py

CMD ["/main.py"]