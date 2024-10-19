import os
import sys
import webbrowser
import threading
import time
from django.core.management import execute_from_command_line

def open_browser():
    time.sleep(2)  # Aguarda 2 segundos para dar tempo do servidor iniciar
    webbrowser.open('http://127.0.0.1:8000')

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gestao_ferias.settings")

    if getattr(sys, 'frozen', False):
        # Executando como executável PyInstaller

        # Aplicar migrações automaticamente
        execute_from_command_line([sys.executable, 'migrate', '--noinput'])
        
        # Criar superusuário se não existir
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        if not User.objects.filter(username='rafael').exists():
            User.objects.create_superuser('rafael', '', '74694821a')
            print("Superusuário 'rafael' criado com sucesso.")

        # Iniciar uma thread para abrir o navegador
        threading.Thread(target=open_browser).start()

        # Iniciar o servidor Django
        execute_from_command_line([sys.executable, 'runserver', '127.0.0.1:8000', '--noreload'])
    else:
        # Executando normalmente, passar os comandos para o Django
        execute_from_command_line(sys.argv)
