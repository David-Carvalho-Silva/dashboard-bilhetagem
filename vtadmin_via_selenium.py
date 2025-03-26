from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
import glob
import shutil

# ===================== CONFIGURAÇÕES GERAIS =====================

download_dir = r"C:\Users\dcdse\OneDrive\Desktop"

def configurar_driver(download_dir=download_dir):
    """
    Configura o WebDriver e retorna a instância do driver.
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")

    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    chrome_options.add_experimental_option("prefs", prefs)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

# ===================== FUNÇÕES AUXILIARES =====================

def fazer_login(driver, usuario, senha):
    """
    Acessa a página de login e realiza o login com usuário e senha fornecidos.
    """
    driver.get("https://vtadmin.manaus.prodatamobility.com.br/")
    
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.ID, "txtLogin"))
    )
    driver.find_element(By.ID, "txtLogin").send_keys(usuario)
    driver.find_element(By.ID, "txtSenha").send_keys(senha)
    driver.find_element(By.ID, "loginbutton").click()

def navegar_para_relatorios(driver):
    """
    Navega pelos menus até chegar na tela de seleção de relatórios.
    """
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "parent_relatorios"))
    )
    driver.find_element(By.ID, "parent_relatorios").click()
    print("✅ Menu 'Relatórios' clicado.")

    geral_menu = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//li[@parent='relatorios']/a[text()='Geral']"))
    )
    geral_menu.click()
    print("✅ Submenu 'Geral' clicado.")

    relatorios_link = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "a.submenuflu[href='Reports/wfm_ReportFilter.aspx']"))
    )
    relatorios_link.click()
    print("✅ Link 'Relatórios' clicado com sucesso.")

    WebDriverWait(driver, 10).until(
        EC.frame_to_be_available_and_switch_to_it((By.ID, "FRAME"))
    )
    print("✅ Mudança para o iframe feita com sucesso.")

def selecionar_relatorio(driver, relatorio):
    """
    Seleciona o relatório desejado (1 - ProviderOrders_v2.rpt ou 2 - BilletsReport_V3.rpt)
    e retorna os elementos para inserir as datas.
    """
    select_element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "select_ddListOpt"))
    )
    select = Select(select_element)

    if relatorio == 1:
        select.select_by_value("ProviderOrders_v2.rpt")
        print("✅ Opção 'Pedidos Provider - V2' selecionada.")
        inicio_id = "DynamicControlProviderOrders_v2.rpt_4"
        fim_id = "DynamicControlProviderOrders_v2.rpt_5"
    else:
        select.select_by_value("BilletsReport_V3.rpt")
        print("✅ Opção 'Boletos Pago (por data de pagamento - V3)' selecionada.")
        inicio_id = "DynamicControlBilletsReport_V3.rpt_7"
        fim_id = "DynamicControlBilletsReport_V3.rpt_8"

    data_inicio = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, inicio_id))
    )
    data_fim = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, fim_id))
    )
    return data_inicio, data_fim

def inserir_datas(data_inicio_element, data_fim_element, data_inicial, data_final):
    """
    Insere as datas nos campos do relatório.
    """
    data_inicio_element.clear()
    data_inicio_element.send_keys(data_inicial)

    data_fim_element.clear()
    data_fim_element.send_keys(data_final)

    print(f"✅ Datas inseridas: {data_inicial} a {data_final}")

def processar_relatorio(driver):
    """
    Clica no botão 'Processar' para gerar o relatório e aguarda a nova janela.
    """
    time.sleep(1)
    driver.find_element(By.ID, "btnQuery").click()
    print("✅ Botão 'Processar' clicado.")

    WebDriverWait(driver, 20).until(lambda d: len(driver.window_handles) > 1)
    driver.switch_to.window(driver.window_handles[1])
    print("✅ Mudança para a nova janela feita com sucesso.")

    WebDriverWait(driver, 120).until(
        EC.frame_to_be_available_and_switch_to_it((By.ID, "frame"))
    )
    print("✅ Mudança para o iframe do relatório feita com sucesso.")

def exportar_relatorio_csv(driver):
    """
    Localiza e clica no botão de exportação, seleciona CSV e confirma a exportação.
    """
    export_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "IconImg_CrystalReportViewer1_toptoolbar_export"))
    )
    export_button.click()
    print("✅ Botão de exportação clicado.")

    dialog_box = WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.XPATH, "//table[contains(@id, '_dialog') and @role='dialog']"))
    )
    print("✅ Modal de exportação detectado.")

    arrow = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//table[contains(@id,'iconMenu_arrow_bobjid') and contains(@id,'_dialog_combo')]"))
    )
    arrow.click()
    print("✅ Seta do combo clicada.")

    time.sleep(1)
    csv_option = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//span[@role='menuitem' and contains(text(), 'Valores separados por caracteres (CSV)')]"))
    )
    driver.execute_script("arguments[0].click();", csv_option)
    print("✅ Formato CSV selecionado.")
    
    exportar_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//a[contains(@id,'_dialog_submitBtn') and text()='Exportar']"))
    )
    exportar_button.click()
    print("✅ Exportação confirmada, download iniciado.")

def mover_csv_para_subpasta(driver, folder_name):
    """
    Aguarda o download, move o último arquivo CSV baixado para a subpasta correspondente.
    """
    time.sleep(90)  # Tempo para efetuar o download
    subfolder_path = os.path.join(download_dir, folder_name)
    if not os.path.exists(subfolder_path):
        os.makedirs(subfolder_path)
        print(f"✅ Pasta '{folder_name}' criada.")
    else:
        print(f"✅ Pasta '{folder_name}' já existe.")
    
    # Busca o arquivo CSV mais recente na pasta de download
    list_of_files = glob.glob(os.path.join(download_dir, "*.csv"))
    if list_of_files:
        latest_file = max(list_of_files, key=os.path.getmtime)
        destination = os.path.join(subfolder_path, os.path.basename(latest_file))
        shutil.move(latest_file, destination)
        print(f"✅ Arquivo movido para {subfolder_path}.")
    else:
        print("Nenhum arquivo CSV encontrado para mover.")

    # Fecha a janela atual do relatório e volta para a principal
    driver.close()
    driver.switch_to.window(driver.window_handles[0])
    # Recarrega o iframe para poder escolher outro relatório
    driver.switch_to.frame("FRAME")

# ===================== FLUXO PRINCIPAL =====================

def main(data_inicial, data_final):
    # As datas agora são recebidas como parâmetros e não são definidas aqui
    # data_inicial = "18/03/2025"
    # data_final   = "19/03/2025"

    # Cria e configura o driver
    driver = configurar_driver(download_dir)
    try:
        # 1) Fazer login
        usuario = "DAVICARVALHO.SNTR"
        senha = "123456"
        fazer_login(driver, usuario, senha)

        # 2) Navegar até a tela de relatórios (uma vez)
        navegar_para_relatorios(driver)

        # === PRIMEIRO RELATÓRIO (Pedidos Provider - V2) ===
        data_inicio_element, data_fim_element = selecionar_relatorio(driver, 1)
        inserir_datas(data_inicio_element, data_fim_element, data_inicial, data_final)
        processar_relatorio(driver)
        exportar_relatorio_csv(driver)
        mover_csv_para_subpasta(driver, "Pedidos Provider - V2")

        # === SEGUNDO RELATÓRIO (Boletos Pago - V3) ===
        data_inicio_element, data_fim_element = selecionar_relatorio(driver, 2)
        inserir_datas(data_inicio_element, data_fim_element, data_inicial, data_final)
        processar_relatorio(driver)
        exportar_relatorio_csv(driver)
        mover_csv_para_subpasta(driver, "Boletos Pago (por data de pagamento - V3)")

        print("✅ Download de ambos relatórios concluído.")
    finally:
        driver.quit()
        print("✅ Driver encerrado.")

if __name__ == "__main__":
    # Caso queira executar diretamente, defina as datas aqui
    main("18/03/2025", "19/03/2025")

