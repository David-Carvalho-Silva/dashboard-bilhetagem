import requests
import random
import time
import json
from bs4 import BeautifulSoup

def qcCript_py(txt):
    """
    Ofusca o texto adicionando 5 caracteres aleatórios entre 65 e 114 a cada caractere original.
    """
    ret = ""
    for c in txt:
        for _ in range(5):
            r = random.randint(65, 114)
            if 91 <= r <= 96:
                r = 76  # 'L'
            ret += chr(r)
        ret += c
    return ret

def login_vtadmin(usuario, senha):
    """
    Realiza login no vtadmin e retorna a sessão autenticada.
    """
    usr_param  = qcCript_py(usuario)
    pass_param = qcCript_py(senha)
    
    session = requests.Session()
    
    # Simula o Internet Explorer
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36"
    })
    
    url_login_async = "https://vtadmin.manaus.prodatamobility.com.br/Login_Async.aspx"
    params = {"usr": usr_param, "pass": pass_param}
    
    response = session.get(url_login_async, params=params)
    print("✅ Login status:", response.status_code)
    
    return session

def post_report_filter(session):
    """
    Envia o POST para processar o relatório e retorna a sessão.
    """
    url = "https://vtadmin.manaus.prodatamobility.com.br/Reports/wfm_ReportFilter.aspx"
    response = session.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    
    viewstate = soup.find("input", {"name": "__VIEWSTATE"}).get("value")
    viewstate_generator = soup.find("input", {"name": "__VIEWSTATEGENERATOR"}).get("value")

    payload = {
        "__EVENTTARGET": "btnQuery",
        "__EVENTARGUMENT": "",
        "__VIEWSTATE": viewstate,
        "__VIEWSTATEGENERATOR": viewstate_generator,
        "ddListOpt": "ProviderOrders_v2.rpt",
        "selectedvalue": "ProviderOrders_v2.rpt",
        "DynamicControlProviderOrders_v2.rpt_4": "10/02/2025",
        "DynamicControlProviderOrders_v2.rpt_5": "12/02/2025",
        "btnQuery": "Processar"
    }

    post_response = session.post(url, data=payload)
    print("✅ Processamento do relatório enviado:", post_response.status_code)
    return session

def capturar_dados_para_exportacao(session):
    """
    Acessa a página ShowReport.aspx para capturar os valores dinâmicos necessários
    para exportar o relatório e aguarda a troca de janela/modal do botão Exportar.
    """
    url_show = "https://vtadmin.manaus.prodatamobility.com.br/Reports/ShowReport.aspx"

    print("⏳ Aguardando 15 segundos para garantir que o relatório seja gerado...")
    time.sleep(15)  # Tempo extra para carregar o relatório

    print("✅ Acessando página de relatório...")
    response = session.get(url_show)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    viewstate = soup.find("input", {"name": "__VIEWSTATE"}).get("value", "")
    viewstate_generator = soup.find("input", {"name": "__VIEWSTATEGENERATOR"}).get("value", "")
    crystal_state_elem = soup.find("input", {"name": "__CRYSTALSTATECrystalReportViewer1"})

    crystal_state = crystal_state_elem.get("value") if crystal_state_elem else ""

    if not crystal_state:
        raise Exception("❌ CRYSTALSTATE não foi encontrado. O relatório pode não ter sido gerado.")

    print("✅ CRYSTALSTATE encontrado!")

    # 🔹 Modificar manualmente `printMode` para `CharacterSeparatedValues`
    try:
        crystal_state_json = json.loads(crystal_state.replace("'", "\""))  # Corrige a string JSON
        crystal_state_json["common"]["printMode"] = "CharacterSeparatedValues"  # Altera para CSV
        crystal_state = json.dumps(crystal_state_json).replace("\"", "'")  # Converte de volta para o formato correto
    except json.JSONDecodeError:
        raise Exception("❌ Erro ao modificar `CRYSTALSTATE`. O formato JSON está incorreto.")

    print("✅ `printMode` alterado para CSV!")
    return viewstate, viewstate_generator, crystal_state

def exportar_csv(session, nome_arquivo="relatorio.csv"):
    """
    Simula o clique no botão 'Exportar', aguarda a troca de janela/modal
    e baixa o relatório em CSV.
    """
    viewstate, viewstate_generator, crystal_state = capturar_dados_para_exportacao(session)

    payload = {
        "__EVENTTARGET": "theBttnbobjid_1740526847058_dialog_submitBtn",
        "__EVENTARGUMENT": "",
        "__CRYSTALSTATECrystalReportViewer1": crystal_state,
        "__VIEWSTATE": viewstate,
        "__VIEWSTATEGENERATOR": viewstate_generator
    }

    url_exportacao = "https://vtadmin.manaus.prodatamobility.com.br/Reports/ShowReport.aspx"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": "https://vtadmin.manaus.prodatamobility.com.br/Reports/ShowReport.aspx",
        "Origin": "https://vtadmin.manaus.prodatamobility.com.br"
    }

    print("📤 Enviando requisição para exportação do relatório...")
    export_resp = session.post(url_exportacao, data=payload, headers=headers)
    export_resp.raise_for_status()

    # Verificar se a resposta contém um arquivo CSV
    content_disposition = export_resp.headers.get("Content-Disposition", "")
    if "attachment" not in content_disposition:
        print("❌ ERRO: O servidor não retornou um CSV válido!")
        print("🔍 Resposta completa do servidor:")
        print(export_resp.text[:2000])
        raise Exception("A exportação falhou, pois o servidor não forneceu um arquivo válido.")

    with open(nome_arquivo, "wb") as f:
        f.write(export_resp.content)

    print(f"✅ Arquivo CSV salvo como {nome_arquivo}.")

# 🔹 Executar o fluxo completo:
if __name__ == "__main__":
    sessao = login_vtadmin("DAVICARVALHO.SNTR", "123456")
    sessao = post_report_filter(sessao)
    exportar_csv(sessao, "relatorio.csv")
