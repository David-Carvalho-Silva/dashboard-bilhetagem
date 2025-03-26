#sript abaixo é tratar_relatorios_envioDB.py
import os
import glob
import pandas as pd
from vtadmin_via_selenium import download_dir 
from vtadmin_via_selenium import main as selenium_main
from sqlalchemy import text
import numpy as np

from db_bilhetagem import get_engine # Importa o diretório de downloads

# Renomeia para maior clareza
base_dir = download_dir

def ler_csv_com_codificacao(arquivo):
    """
    Tenta ler o arquivo CSV utilizando diferentes codificações, sem interpretar
    a primeira linha como cabeçalho (header=None).
    """
    encodings = ['utf-8', 'ISO-8859-1', 'windows-1252']
    for enc in encodings:
        try:
            # Lê o CSV sem cabeçalho para que todos os dados sejam tratados como dados
            return pd.read_csv(arquivo, encoding=enc, header=None), enc
        except UnicodeDecodeError:
            continue
    return None, None

def tratar_pedidos_provider_v2(base_dir):
    """
    Processa os arquivos CSV encontrados na pasta 'Pedidos Provider - V2'.
    
    Etapas de tratamento:
      1. Remove as 7 primeiras colunas.
      2. Na primeira coluna que sobrou, remove a string "Empresa:" de todos os dados.
      3. Exclui as colunas de índice 1 a 10, mantendo apenas a de índice 2.
      4. Remove todas as colunas completamente vazias.
      5. Remove as 3 últimas colunas.
      6. Atribui novos títulos: ["Empresa", "Código da Empresa", "Nº Pedido", "Data do Pedido", "Taxa Adm.", "Valor Crédito", "Status"].

    Retorna:
      Uma lista de DataFrames resultantes do tratamento de cada arquivo CSV.
    """
    pasta_name = "Pedidos Provider - V2"
    pasta_path = os.path.join(base_dir, pasta_name)
    dataframes_resultantes = []  # Lista para armazenar os DataFrames finais
    
    if not os.path.exists(pasta_path):
        print(f"🚫 Pasta '{pasta_name}' não encontrada.")
        return dataframes_resultantes  # Retorna lista vazia

    arquivos_csv = glob.glob(os.path.join(pasta_path, "*.csv"))
    if not arquivos_csv:
        print("❌ Nenhum arquivo CSV encontrado na pasta.")
        return dataframes_resultantes  # Retorna lista vazia

    for arquivo in arquivos_csv:
        print(f"📄 Processando o arquivo: {arquivo}")
        df, encoding_usada = ler_csv_com_codificacao(arquivo)
        if df is None:
            print(f"⚠ Erro ao ler o arquivo {arquivo}")
            continue
        
        print(f"✅ Arquivo lido com sucesso utilizando codificação '{encoding_usada}'.")

        # Remover as 7 primeiras colunas
        if df.shape[1] <= 7:
            print("⚠ O arquivo possui 7 ou menos colunas. Não é possível remover as 7 primeiras colunas.")
            continue
        df_tratado = df.iloc[:, 7:]
        print("📝 DataFrame após remover as 7 primeiras colunas:")
        #print(df_tratado.head())

        # Na primeira coluna (índice 0) remova "Empresa:" dos valores e limpe espaços extras
        df_tratado.iloc[:, 0] = (
            df_tratado.iloc[:, 0]
            .astype(str)
            .str.replace("Empresa:", "", regex=False)
            .str.strip()
        )
        print("📝 DataFrame após remover 'Empresa:' da primeira coluna (dados):")
        #print(df_tratado.head())

        # Excluir as colunas de índice 1 a 10, mantendo a de índice 2
        indices_para_remover = [i for i in range(1, 11) if i != 2]
        colunas_para_remover = [
            df_tratado.columns[i] for i in indices_para_remover if i < len(df_tratado.columns)
        ]
        df_tratado = df_tratado.drop(columns=colunas_para_remover)
        print("📝 DataFrame após remover colunas de índice 1 a 10 (exceto índice 2):")
        #print(df_tratado.head())

        # Remover colunas completamente vazias
        df_tratado = df_tratado.dropna(axis=1, how='all')
        print("📝 DataFrame após remover colunas completamente vazias:")
        #print(df_tratado.head())

        # Remover as 3 últimas colunas, se houver pelo menos 3 colunas disponíveis
        if df_tratado.shape[1] > 3:
            df_tratado = df_tratado.iloc[:, :-3]
            print("📝 DataFrame após remover as 3 últimas colunas:")
            #print(df_tratado.head())
        else:
            print("⚠ Não há colunas suficientes para remover as 3 últimas.")

        # Definir os novos títulos das colunas
        novos_titulos = ["Empresa", "Código da Empresa", "Nº Pedido", "Data do Pedido", "Taxa Adm.", "Valor Crédito", "Status"]
        if df_tratado.shape[1] == len(novos_titulos):
            df_tratado.columns = novos_titulos
            print("📝 DataFrame com colunas renomeadas:")
            print(df_tratado.head())
        else:
            print(f"⚠ Atenção: Número de colunas ({df_tratado.shape[1]}) difere do esperado ({len(novos_titulos)}).")
        
        
        # Excluir linhas com os códigos indesejados na coluna "Código da Empresa"
        if "Código da Empresa" in df_tratado.columns:
            codigos_excluir = [77776, 99999, 3, 27717, 99998, 77777, 77778,28671,
                               142,5823,24023,]
            df_tratado = df_tratado[~df_tratado["Código da Empresa"].isin(codigos_excluir)]
            print("🗑️ Linhas com os códigos indesejados foram removidas:", codigos_excluir)
        else:
            print("⚠ Coluna 'Código da Empresa' não encontrada para realizar a exclusão.")

        
        print("-" * 40)
        
        # Adiciona o DataFrame tratado à lista de resultados
        dataframes_resultantes.append(df_tratado)

    return dataframes_resultantes

def tratar_boletos_pago_v3(base_dir):
    """
    Processa os arquivos CSV encontrados na pasta "Boletos Pago (por data de pagamento - V3)".

    Fluxo do tratamento:
      - Seleciona as primeiras 20 colunas e mantém somente a coluna 10 (índice 9) e a coluna 12 (índice 11).
      - Mantém todas as colunas a partir da 21ª (índice 20 em diante).
      - Concatena esses conjuntos para formar o DataFrame final.
      - Exclui as duas últimas colunas do DataFrame final.
      - Renomeia as colunas resultantes para:
        [ "Banco", "Empresa", "Emissão", "Pagamento", "Processado", "Liberação", 
          "Nosso Número", "Número Pedido", "Valor Pedido", "Valor" ]

    Retorna:
      Uma lista de DataFrames resultantes do tratamento de cada arquivo CSV.
    """
    pasta_name = "Boletos Pago (por data de pagamento - V3)"
    pasta_path = os.path.join(base_dir, pasta_name)
    dataframes_resultantes = []  # Lista para armazenar os DataFrames finais
    
    if not os.path.exists(pasta_path):
        print(f"🚫 Pasta '{pasta_name}' não encontrada.")
        return dataframes_resultantes

    arquivos_csv = glob.glob(os.path.join(pasta_path, "*.csv"))
    if not arquivos_csv:
        print("❌ Nenhum arquivo CSV encontrado na pasta.")
        return dataframes_resultantes

    for arquivo in arquivos_csv:
        print(f"📄 Processando o arquivo: {arquivo}")
        df, encoding_usada = ler_csv_com_codificacao(arquivo)
        if df is None:
            print(f"⚠ Erro ao ler o arquivo {arquivo}")
            continue
        
        print(f"✅ Arquivo lido com sucesso utilizando codificação '{encoding_usada}'.")
        print(df.iloc[-5:, 10:18])

        # Verifica se a última linha tem menos colunas do que deveria
        if df.iloc[-1].isnull().sum() > 0:  # Confirma que há colunas ausentes na última linha
            # Copia a última linha problemática
            last_row = df.iloc[-1].copy()
            new_row = last_row.copy()

            # Pega todos os valores a partir da coluna 11 (índice 10)
            valores = new_row.iloc[10:].values

            # Cria uma lista com o novo alinhamento: insere None no início e desloca os demais para a direita
            novos_valores = [np.nan]  + list(valores[:-1])

            # Atribui os novos valores às colunas a partir da coluna 11
            new_row.iloc[10:] = novos_valores

            # Insere a nova linha no final do DataFrame
            df = pd.concat([df, new_row.to_frame().T], ignore_index=True)

            # Exclui a penúltima linha (a linha original desalinhada)
            df = df.drop(df.index[-2]).reset_index(drop=True)



            print("✅ Última linha ajustada.")
            print(df.iloc[-5:, 10:18])
        
        # Verifica se o DataFrame possui ao menos 20 colunas para a primeira etapa
        if df.shape[1] < 20:
            print("⚠ O arquivo não possui 20 colunas. Pulando este arquivo.")
            continue

        # Seleciona as primeiras 20 colunas
        df_first20 = df.iloc[:, :20]
        # Mantém somente a coluna 10 (índice 9) e a coluna 12 (índice 11)
        df_keep = df_first20.iloc[:, [9, 11]]
        # Mantém todas as colunas a partir da 21ª (índice 20 em diante)
        df_remaining = df.iloc[:, 20:]
        # Concatena os conjuntos horizontalmente
        df_tratado = pd.concat([df_keep, df_remaining], axis=1)
        
        # Exclui as duas últimas colunas do DataFrame final
        if df_tratado.shape[1] < 2:
            print("⚠ O DataFrame não possui colunas suficientes para remover as duas últimas.")
            continue
        df_tratado = df_tratado.iloc[:, :-2]

        # Renomeia as colunas para os nomes desejados
        colunas_finais = [
            "Banco", "Empresa", "Emissão", "Pagamento", "Processado", 
            "Liberação", "Nosso Número", "Número Pedido", "Valor Pedido", "Valor"
        ]
        
        if df_tratado.shape[1] == len(colunas_finais):
            df_tratado.columns = colunas_finais
            print("📝 DataFrame final com colunas renomeadas:")
            print(df_tratado.head())
        else:
            print(f"⚠ O DataFrame final não possui {len(colunas_finais)} colunas. Atual: {df_tratado.shape[1]}")
        
        print("-" * 40)
        
        # Adiciona o DataFrame tratado à lista de resultados
        dataframes_resultantes.append(df_tratado)

    return dataframes_resultantes



# As funções abaixo (selenium_main, tratar_pedidos_provider_v2, tratar_boletos_pago_v3, base_dir e get_engine)
# devem estar definidas em seu projeto.


def remove_duplicados(engine, tabela):
    """
    Remove registros duplicados (todas as colunas iguais) da tabela especificada.
    """
    with engine.begin() as conn:
        temp_table = f"temp_{tabela}"
        print(f"🧹 Removendo duplicados da tabela {tabela}...")
        conn.execute(text(f"CREATE TABLE {temp_table} AS SELECT DISTINCT * FROM {tabela};"))
        conn.execute(text(f"TRUNCATE TABLE {tabela};"))
        conn.execute(text(f"INSERT INTO {tabela} SELECT * FROM {temp_table};"))
        conn.execute(text(f"DROP TABLE {temp_table};"))
        print(f"✅ Duplicados removidos da tabela {tabela}.")


    
def delete_registros_intervalo(engine, tabela, data_inicial, data_final):
    """
    Apaga os registros da tabela que possuem a "Data do Pedido" 
    entre data_inicial e data_final (inclusive) e retorna a quantidade de registros apagados.

    Parâmetros:
      - engine: objeto de conexão com o banco.
      - tabela: nome da tabela onde os registros serão deletados.
      - data_inicial: data inicial no formato "dd/mm/yyyy".
      - data_final: data final no formato "dd/mm/yyyy".
    """
    with engine.begin() as conn:
        print(f"🧹 Deletando registros da tabela {tabela} entre {data_inicial} e {data_final}...")
        query = f"""
            DELETE FROM {tabela}
            WHERE STR_TO_DATE(`Data do Pedido`, '%d/%m/%Y') BETWEEN 
                  STR_TO_DATE(:data_inicial, '%d/%m/%Y') AND STR_TO_DATE(:data_final, '%d/%m/%Y')
        """
        result = conn.execute(text(query), {"data_inicial": data_inicial, "data_final": data_final})
        deleted_count = result.rowcount
        print(f"✅ Registros deletados: {deleted_count}.")
    return deleted_count

def remove_duplicados_por_num_pedido(engine, tabela, pk="id"):
    """
    Remove registros duplicados mantendo apenas um registro para cada 'Nº Pedido',
    de modo que seja preservado o registro com o maior valor de {pk} (mais recente).
    """
    try:
        with engine.begin() as conn:
            temp_table = f"temp_{tabela}"
            print(f"🧹 Removendo duplicados da tabela '{tabela}' com base em 'Nº Pedido', mantendo o maior {pk}...")

            # Verificar se existem dados na tabela antes de processar
            count_query = f"SELECT COUNT(*) FROM db_bilhetagem.{tabela}"
            count = conn.execute(text(count_query)).scalar()
            print(f"Registros na tabela original antes do processamento: {count}")
            
            if count == 0:
                print(f"⚠️ Nenhum registro encontrado em {tabela}. Pulando processamento.")
                return

            # Se a tabela temporária já existir, removê-la
            conn.execute(text(f"DROP TABLE IF EXISTS db_bilhetagem.{temp_table};"))

            # 1. Cria uma tabela temporária com a mesma estrutura da tabela original.
            conn.execute(text(f"CREATE TABLE db_bilhetagem.{temp_table} LIKE db_bilhetagem.{tabela};"))

            # 2. Insere na tabela temporária apenas os registros que possuem o maior {pk} para cada 'Nº Pedido'
            insert_query = f"""
                INSERT INTO db_bilhetagem.{temp_table}
                SELECT t.*
                FROM db_bilhetagem.{tabela} AS t
                JOIN (
                    SELECT `Nº Pedido`, MAX({pk}) AS max_id
                    FROM db_bilhetagem.{tabela}
                    GROUP BY `Nº Pedido`
                ) AS filtro
                ON t.{pk} = filtro.max_id;
            """

            result = conn.execute(text(insert_query))
            print(f"Linhas inseridas na tabela temporária: {result.rowcount}")

            # Verificar dados na tabela temporária
            temp_count = conn.execute(text(f"SELECT COUNT(*) FROM db_bilhetagem.{temp_table}")).scalar()
            print(f"Registros na tabela temporária: {temp_count}")

            # 3. Limpa a tabela original
            conn.execute(text(f"TRUNCATE TABLE db_bilhetagem.{tabela};"))

            # 4. Reinsere os registros filtrados de volta na tabela original
            result2 = conn.execute(text(f"INSERT INTO db_bilhetagem.{tabela} SELECT * FROM db_bilhetagem.{temp_table};"))
            print(f"Registros reinseridos na tabela original: {result2.rowcount}")

            # 5. Remove a tabela temporária
            conn.execute(text(f"DROP TABLE db_bilhetagem.{temp_table};"))

            print(f"✅ Duplicados removidos de '{tabela}' mantendo apenas o registro com maior {pk}.")
    except Exception as e:
        print(f"❌ Erro ao processar tabela {tabela}: {str(e)}")



def main():
     # Defina as datas aqui no script principal
    data_inicial = "01/03/2025"
    data_final   = "25/03/2025"

    # Executa o Selenium passando as datas definidas
    selenium_main(data_inicial, data_final)

    # 1) Gera as listas de DataFrames
    df_pedidos_list = tratar_pedidos_provider_v2(base_dir)
    df_boletos_list = tratar_boletos_pago_v3(base_dir)

    print(f"Total de DataFrames retornados de Pedidos Provider: {len(df_pedidos_list)}")
    print(f"Total de DataFrames retornados de Boletos Pago V3: {len(df_boletos_list)}")

    # 2) Cria a engine para se conectar ao banco MySQL
    engine = get_engine()

    # 3) Deleta apenas os registros do período definido (sem afetar outros meses)
    delete_registros_intervalo(engine, "pedidos_provider_v2", data_inicial, data_final)

    # 3) Insere cada DataFrame de Pedidos Provider - V2 na tabela 'pedidos_provider_v2'
    for i, df_pedidos in enumerate(df_pedidos_list, start=1):
        print(f"Inserindo DataFrame {i} de Pedidos Provider - V2 na tabela 'pedidos_provider_v2'...")
        df_pedidos.to_sql(
            name="pedidos_provider_v2",
            con=engine,
            if_exists="append",
            index=False
        )

    # 4) Insere cada DataFrame de Boletos Pago - V3 na tabela 'boletos_pago_v3'
    for i, df_boletos in enumerate(df_boletos_list, start=1):
        print(f"Inserindo DataFrame {i} de Boletos Pago - V3 na tabela 'boletos_pago_v3'...")
        df_boletos.to_sql(
            name="boletos_pago_v3",
            con=engine,
            if_exists="append",
            index=False
        )

    # 5) Após as inserções, remove duplicados das tabelas no próprio banco de dados
    
    remove_duplicados(engine, "boletos_pago_v3")
    remove_duplicados_por_num_pedido(engine, "pedidos_provider_v2", pk="id")
    #remove_duplicados_pedidos_provider_v2(engine)

    print("✅ Inserção e limpeza concluídas.")

if __name__ == "__main__":
    main()

