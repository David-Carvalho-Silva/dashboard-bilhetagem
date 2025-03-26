from sqlalchemy import create_engine

def get_engine():
    """
    Retorna uma engine SQLAlchemy conectada ao MySQL.
    Altere user, password, host, db_name conforme seu ambiente.
    """
    user = "root"               # Usando root
    password = "password" # Coloque a senha do root aqui
    host = "localhost"
    db_name = "db_bilhetagem"    # Seu banco de dados

    engine_url = f"mysql+pymysql://{user}:{password}@{host}/{db_name}"
    engine = create_engine(engine_url, echo=False)
    return engine


