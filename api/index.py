# api/index.py

from vercel import make_wsgi_handler
from dash_bilhetagem import app  # importa seu Dash (onde app = dash.Dash(...))

# O Vercel precisa de uma função "handler" que atenda as requests
handler = make_wsgi_handler(app.server)
