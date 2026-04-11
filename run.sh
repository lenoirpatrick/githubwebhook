#/bin/bash
pip install -r requirements.txt --break-system-packages

rm -rf nohup.out
nohup python gitpull.py &