# llm-agents

## ⚠️ IMPORTANT DISCLAIMER ⚠️

**THIS PROJECT IS NOT FINANCIAL ADVICE IN ANY WAY AND SHOULD NOT BE USED AS SUCH.**

This repository and all its contents are provided "as-is" for **educational and experimental purposes only**. 

### 🚫 NOT FINANCIAL ADVICE
The information, tools, portfolio analysis, backtesting results, or any data provided within this repository are **NOT** intended to be, and should **NOT** be construed as, financial, investment, legal, or professional advice of any kind. **DO NOT** make any financial decisions based on the information presented here. Always consult with a qualified financial professional before making any investment decisions.

### 💸 NO LIABILITY FOR FINANCIAL LOSSES
The contributors, maintainers, and creators of this repository **DISCLAIM ALL LIABILITY** and are **NOT RESPONSIBLE** for any financial losses, damages, or liabilities that may arise directly or indirectly from the use of, or reliance on, the information, tools, or data contained herein. By using this repository, you acknowledge and agree that you do so **AT YOUR OWN SOLE RISK**.

### 📊 EXPERIMENTAL TOOLS ONLY
All portfolio analysis, backtesting, and financial calculations are experimental tools for learning purposes only. Past performance does not indicate future results. Financial markets are inherently risky and unpredictable.

### ⚖️ LEGAL PROTECTION
This project is licensed under the MIT License, which provides additional legal protection by disclaiming warranties and limiting liability. See the [LICENSE](LICENSE) file for full terms.

**By using this software, you acknowledge that you understand and agree to these terms.**

-------

## Setup Instructions

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

Or try out at https://portfoliomate.streamlit.app

docker-compose up -d --build