# llm-agents

- Step 1: install Python3.10 and `virtualenv`
```bash
brew install python@3.10
pip install virtualenv
```

- Step 2: create virtual env (from the project root folder)
```bash
virtualenv -p python3.10 .venv
```
Active your virtual environment:
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

- Step 3: install dependencies
Upgrade python pip first
```bash
python -m pip install --upgrade pip
```
Install dependencies, also switch to `src/python` folder
```bash
cd src/python
pip install -r requirements.txt
```
