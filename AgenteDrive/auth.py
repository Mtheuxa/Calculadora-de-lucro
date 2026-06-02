import os
import pickle
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Escopos necessários para ler arquivos no Google Drive
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def get_drive_service():
    """Mostra o fluxo de autenticação e retorna o serviço da API do Drive."""
    creds = None
    
    # O arquivo token.pickle armazena os tokens de acesso e atualização do usuário,
    # e é criado automaticamente quando o fluxo de autorização for concluído pela primeira vez.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
            
    # Se não houver credenciais válidas, permite que o usuário faça o login.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Erro ao atualizar o token: {e}")
                creds = None
        
        if not creds:
            if not os.path.exists('credentials.json'):
                print("\n" + "="*50)
                print("ERRO: O arquivo 'credentials.json' não foi encontrado.")
                print("="*50)
                print("Para que o agente acesse seu Google Drive, siga estes passos:")
                print("1. Acesse o Google Cloud Console (https://console.cloud.google.com/)")
                print("2. Crie um novo projeto.")
                print("3. Ative a 'Google Drive API' para este projeto.")
                print("4. Vá em 'Credenciais' > 'Criar Credenciais' > 'ID do cliente OAuth'.")
                print("5. Escolha 'Aplicativo de computador'.")
                print("6. Baixe o arquivo JSON gerado e renomeie para 'credentials.json'.")
                print("7. Salve o arquivo na mesma pasta deste script.")
                print("="*50 + "\n")
                return None
                
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            
            # Tenta forçar a abertura no Google Chrome
            import webbrowser
            chrome_path = "C:/Program Files/Google/Chrome/Application/chrome.exe"
            if not os.path.exists(chrome_path):
                chrome_path = "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"
            
            if os.path.exists(chrome_path):
                webbrowser.register('chrome', None, webbrowser.BackgroundBrowser(chrome_path))
                creds = flow.run_local_server(port=0, browser='chrome')
            else:
                # Fallback caso não encontre o Chrome instalado
                creds = flow.run_local_server(port=0)
            
        # Salva as credenciais para a próxima execução
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('drive', 'v3', credentials=creds)
    return service
