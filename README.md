# grass-vpn

## usage

### first usage 
```
docker network create --driver bridge --subnet 172.2.0.0/16 vpn
python3 -m venv ./.venv
source ./.venv/bin/activate
pip install -r requirements.txt
cp ./.env_template ./.env
```

### For .env

for GRASS_USERID and API_KEY
in logined grass web console run
```
localStorage.getItem('accessToken');
localStorage.getItem('userId');
```

### gerneral usage 

```
source ./.venv/bin/activate
python3 ./run.py 
```
# Referrals
if it help you. Please use my Referrals code.
https://app.getgrass.io/register/?referralCode=hQ0bvpT7r02R51x

# Reference
https://github.com/aron-666/Aron-vpngate-client-docker
https://github.com/ymmmmmmmm/getgrass_bot