# Capstone
this is the Capstone project 


command to get started:

open one terminal

do like a clean slate setup (to avoid issues)

npm cache clean --force
rm -rf node_modules package-lock.json
npm install

then 
npm run dev

check the site at 
http://localhost:3000


open another terminal (don't close the other one)

cd backend 
python3 -m venv venv 
source venv/bin/activate

put the openai api key in the .env

pip install -r requirements.txt

make sure it's all installed

uvicorn main:app --reload

to start the dockerfile

cd docker 

(start running docker on the background)

docker compose -f docker/docker-compose.yml up --build