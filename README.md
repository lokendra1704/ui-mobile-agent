# ui-mobile-agent

### Steps To Run
- In the project root, Copy `.env.sample` and paste it to `.env` file and change values accordingly.
- Run `setup.sh` file to setup python virtual environment and install dependencies.
```
sudo chmod 777 setup.sh
./setup.sh
```
- Run src/main.py with user query as first argument. Example: `python src/main.py "Open Youtube"`