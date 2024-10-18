import os
import sys
import webbrowser
import threading
import time

def open_browser():
    time.sleep(2)  # Aguarda 2 segundos para dar tempo do servidor iniciar
    webbrowser.open('http://127.0.0.1:8000')

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gestao_ferias.settings")

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    # Verificar se o comando runserver foi passado, se não, adicionar automaticamente
    if len(sys.argv) == 1 or sys.argv[1] != 'runserver':
        sys.argv = [sys.argv[0], 'runserver', '127.0.0.1:8000']

    # Iniciar o servidor Django com a flag --noreload
    if '--noreload' not in sys.argv:
        sys.argv.append('--noreload')

    # Iniciar uma thread para abrir o navegador
    threading.Thread(target=open_browser).start()

    # Executar o servidor Django
    execute_from_command_line(sys.argv)
