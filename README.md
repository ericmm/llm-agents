# llm-agents

- Step 1: install Python3.10 and `virtualenv` (only need to do this step once)
```bash
brew install python@3.10
pip install virtualenv
```

- Step 2: create virtual env (**from the project root folder**, only need to do this step once)
```bash
virtualenv -p python3.10 .venv
```
Upgrade python pip first
```bash
python -m pip install --upgrade pip
```

- Step 3: Active your virtual environment:
```bash
source .venv/bin/activate
```
You can confirm the python version by following command, it should output 3.10.xx:
```bash
python --version
which python
```
When you want to switch back to system default Python, you can use deactivate command:
```bash
deactivate
```

- Step 4: install dependencies (please switch to `src/python` folder)
```bash
cd src/python
pip install -r requirements.txt
```

- Step 5: Run llm agents 
startup FreeGPT3.5 docker, it opens a port on 3040 
```bash
cd ../..
docker-compose up -d
```
run the llm agents app
```bash
cd src/python
python gpt35_agent.py
```

- Step 6: Run the webpage app (make sure you are in `src/python` folder)
```bash
streamlit run portfolio_mate.py
```
The app is available on http://localhost:8501