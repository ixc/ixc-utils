FROM python:3.10

##RUN chmod a+r /dev/ptp0
RUN mkdir /opt/ixc-utils
RUN mkdir /opt/ixc-utils/ixc_utils
##COPY ixc_utils/*.py /opt/ixc-utils/ixc_utils
COPY ixcu/*.py /opt/ixc-utils/ixc_utils

CMD python3 /opt/ixc-utils/ixc_utils/time.py poll
ENTRYPOINT env
