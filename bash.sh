#!/bin/bash

# Ensure we are using the environment's python
python isimip3b_anomalies.py --region global --scenario ssp126 &
python isimip3b_anomalies.py --region global --scenario ssp245 &
python isimip3b_anomalies.py --region global --scenario ssp370 &
python isimip3b_anomalies.py --region global --scenario ssp585 &
python isimip3b_anomalies.py --region global --scenario piControl &

wait
echo "All parallel scenarios have finished."
