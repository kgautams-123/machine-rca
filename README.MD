#Host Streamlit on EC2

Note: Do the port mapping to this port:- 8501
sudo apt update
sudo apt-get update
sudo apt upgrade -y
sudo apt install git curl unzip tar make sudo vim wget -y
sudo apt install git curl unzip tar make sudo vim wget -y
git clone "Your-repository"
sudo apt install python3-pip
pip3 install -r requirements.txt
#if above doesnt work
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
#Temporary running
python3 -m streamlit run streamlit_app.py
#Permanent running
nohup python3 -m streamlit run streamlit_app.py
Note: Streamlit runs on this port: 8501