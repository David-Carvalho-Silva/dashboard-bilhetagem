import requests
import random

def qcCript_py(txt):
    ret = ""
    for c in txt:
        for _ in range(5):
            r = random.randint(65, 114)
            if 91 <= r <= 96:
                r = 76  # 'L'
            ret += chr(r)
        ret += c
    return ret

# Credenciais em texto puro
usuario = "DAVICARVALHO.SNTR"
senha   = "123456"

# Transforma com qcCript
usr_param  = qcCript_py(usuario)
pass_param = qcCript_py(senha)

# Cria sessão
session = requests.Session()

# Faz a requisição GET no endpoint assíncrono
url_login_async = "https://vtadmin.manaus.prodatamobility.com.br/Login_Async.aspx"
params = {"usr": usr_param, "pass": pass_param}

response = session.get(url_login_async, params=params)

#print("Status:", response.status_code)
#print("Resposta (início):", response.text[:200])
#print("Cookies:", session.cookies.get_dict())

report_url = "https://vtadmin.manaus.prodatamobility.com.br/Reports/wfm_ReportFilter.aspx"
report_response = session.get(report_url)
#print(report_response.status_code)
#print(report_response.text)

from bs4 import BeautifulSoup

# 1. Faça o login e processe o relatório (como antes)
session = requests.Session()
# ... login e post_report_filter ...

# 2. GET na página wfm_LaunchReport.aspx
resp = session.get("https://vtadmin.manaus.prodatamobility.com.br/Reports/wfm_LaunchReport.aspx")
html = resp.text

# 3. Verifique se alguma informação do relatório aparece no texto
if "CONNIN CONSTRUÇÃO" in html or "915739" in html:
    print("Achei parte dos dados no HTML!")
else:
    print("Não encontrei as informações no HTML bruto.")

# 4. Se encontrar, parse com BeautifulSoup
soup = BeautifulSoup(html, "html.parser")
# Exemplo: procurar tags <table> e <td>
tables = soup.find_all("table")
for t in tables:
    print("Tabela encontrada:", t)
    # Tente localizar as linhas/colunas com a informação


