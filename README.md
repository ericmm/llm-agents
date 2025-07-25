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

Or try out at https://portfoliomate.streamlit.app

-------
## Disclaimer

This repository and its contents are provided "as-is" and for informational and educational purposes only.

**No Financial Advice**: The information, tools, or data provided within this repository are not intended to be, and should not be construed as, financial, investment, legal, or professional advice of any kind. You should not make any financial decisions based solely on the information presented here. Always consult with a qualified financial professional before making any investment decisions.

**No Responsibility for Financial Loss**: The contributors, maintainers, and creators of this repository are not responsible for any financial losses, damages, or liabilities that may arise directly or indirectly from the use of, or reliance on, the information, tools, or data contained herein. By using this repository, you acknowledge and agree that you do so at your own sole risk.

**Accuracy and Completeness**: While efforts have been made to ensure the accuracy and completeness of the information within this repository, we make no guarantees, representations, or warranties, express or implied, regarding its reliability, accuracy, completeness, or suitability for any particular purpose. The content may be outdated or contain errors.

**Use at Your Own Risk**: Any actions you take based on the information or tools in this repository are strictly at your own discretion and risk.
