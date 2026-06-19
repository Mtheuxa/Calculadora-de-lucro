import os
import time
import io
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# Escopos básicos para ler/gravar no Drive
SCOPES = ['https://www.googleapis.com/auth/drive']

class DriveService:
    def __init__(self, credentials_file='credentials.json', token_file='token.json'):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.creds = None
        self.service = None
        self.authenticate()

    def authenticate(self):
        """Realiza o processo de autenticação OAuth2 com a API do Google Drive."""
        if os.path.exists(self.token_file):
            self.creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
        
        # Se as credenciais não forem válidas, faça login.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(f"Arquivo '{self.credentials_file}' não encontrado. Baixe do Google Cloud Console.")
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES)
                self.creds = flow.run_local_server(port=0)
            
            # Salva as credenciais para o próximo uso
            with open(self.token_file, 'w') as token:
                token.write(self.creds.to_json())
                
        self.service = build('drive', 'v3', credentials=self.creds)

    def get_or_create_folder(self, folder_name, parent_id=None):
        """
        Busca por uma pasta com o nome especificado dentro do parent_id.
        Se não existir, cria a pasta e retorna seu ID.
        """
        # Escapando aspas simples no nome da pasta
        safe_name = folder_name.replace("'", "\\'")
        query = f"name = '{safe_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed=false"
        if parent_id:
            query += f" and '{parent_id}' in parents"

        response = self.service.files().list(q=query, spaces='drive', fields='files(id, name)', supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
        files = response.get('files', [])

        if files:
            return files[0].get('id')
        else:
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            if parent_id:
                folder_metadata['parents'] = [parent_id]
                
            folder = self.service.files().create(body=folder_metadata, fields='id', supportsAllDrives=True).execute()
            print(f"Pasta '{folder_name}' criada com ID: {folder.get('id')}")
            return folder.get('id')

    def create_path(self, path_list, root_parent_id):
        """
        Cria a hierarquia de pastas se não existirem e retorna o ID da última pasta.
        """
        current_parent_id = root_parent_id
        for folder in path_list:
            current_parent_id = self.get_or_create_folder(folder, current_parent_id)
        return current_parent_id

    def copy_file(self, source_file_id, new_name, parent_id):
        """Copia um arquivo no Drive de um local para outro."""
        # Verifica se já existe um arquivo com esse nome no destino
        safe_name = new_name.replace("'", "\\'")
        query = f"name = '{safe_name}' and '{parent_id}' in parents and trashed=false"
        response = self.service.files().list(q=query, spaces='drive', fields='files(id)', supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
        files = response.get('files', [])
        if files:
            print(f"Arquivo '{new_name}' já existe no destino. Ignorando...")
            return files[0].get('id')

        body = {
            'name': new_name,
            'parents': [parent_id]
        }
        
        try:
            copied_file = self.service.files().copy(
                fileId=source_file_id,
                body=body,
                supportsAllDrives=True
            ).execute()
            print(f"Copiado -> '{new_name}'")
            return copied_file.get('id')
        except Exception as e:
            print(f"Erro ao copiar {new_name}: {e}")
            return None

    def walk_folder(self, folder_id, path_prefix="", allowed_root_folders=None):
        """
        Retorna um gerador que lista recursivamente todos os arquivos dentro de uma pasta do Drive.
        Yields dicionários: {'name': name, 'id': id, 'path': logical_path}
        """
        query = f"'{folder_id}' in parents and trashed=false"
        page_token = None
        
        while True:
            for attempt in range(5):
                try:
                    response = self.service.files().list(
                        q=query,
                        spaces='drive',
                        fields='nextPageToken, files(id, name, mimeType)',
                        pageToken=page_token,
                        supportsAllDrives=True,
                        includeItemsFromAllDrives=True
                    ).execute()
                    break
                except Exception as e:
                    print(f"Aviso: Erro de conexão, tentando novamente ({attempt+1}/5)...")
                    time.sleep(2)
            else:
                print(f"Erro fatal: Não foi possível ler a pasta {folder_id} após 5 tentativas.")
                break
                
            for file in response.get('files', []):
                logical_path = f"{path_prefix}/{file.get('name')}" if path_prefix else file.get('name')
                if file.get('mimeType') == 'application/vnd.google-apps.folder':
                    # Pula pastas na raiz que não estão na lista de permitidas (se a lista não estiver vazia)
                    if not path_prefix and allowed_root_folders:
                        if file.get('name') not in allowed_root_folders:
                            continue
                    
                    print(f"Lendo subpasta: {logical_path}")
                    yield from self.walk_folder(file.get('id'), logical_path, allowed_root_folders)
                else:
                    yield {
                        'id': file.get('id'),
                        'name': file.get('name'),
                        'path': logical_path
                    }
            
            page_token = response.get('nextPageToken', None)
            if page_token is None:
                break

    def download_file_to_memory(self, file_id):
        """Baixa o arquivo para a memória e retorna os bytes."""
        try:
            request = self.service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            fh.seek(0)
            return fh
        except Exception as e:
            print(f"Erro ao baixar arquivo {file_id}: {e}")
            return None

    def get_folder_name(self, folder_id):
        """Obtém o nome de uma pasta ou arquivo pelo ID."""
        try:
            folder = self.service.files().get(fileId=folder_id, fields='name', supportsAllDrives=True).execute()
            return folder.get('name')
        except Exception as e:
            print(f"Erro ao obter nome da pasta {folder_id}: {e}")
            return None
