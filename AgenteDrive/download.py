import os
import io
from googleapiclient.http import MediaIoBaseDownload

# Define para onde exportar arquivos nativos do Google Docs/Sheets
EXPORT_MIME_TYPES = {
    'application/vnd.google-apps.document': {
        'export': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'ext': '.docx'
    },
    'application/vnd.google-apps.spreadsheet': {
        'export': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'ext': '.xlsx'
    },
    'application/vnd.google-apps.presentation': {
        'export': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'ext': '.pptx'
    }
}

def download_file(service, file_info, base_dir="Downloads"):
    """
    Baixa um arquivo do Google Drive. Exporta se for formato Google (Docs/Sheets).
    """
    file_id = file_info['id']
    file_name = file_info['name']
    mime_type = file_info.get('mimeType', '')
    curso = file_info.get('curso', 'Desconhecido')
    
    # Evitar caracteres inválidos em nomes de pasta
    curso_seguro = "".join([c for c in curso if c.isalnum() or c in (' ', '-', '_')]).strip()
    if not curso_seguro:
        curso_seguro = "Outros"
        
    curso_dir = os.path.join(base_dir, curso_seguro)
    os.makedirs(curso_dir, exist_ok=True)
    
    # Verifica se é um arquivo do Google (Docs/Sheets/Slides) e ajusta o download
    if mime_type in EXPORT_MIME_TYPES:
        export_info = EXPORT_MIME_TYPES[mime_type]
        request = service.files().export_media(fileId=file_id, mimeType=export_info['export'])
        if not file_name.endswith(export_info['ext']):
            file_name += export_info['ext']
    else:
        # Formatos nativos (PDF, Word original, Excel original)
        request = service.files().get_media(fileId=file_id)
        
    # Limpa nome do arquivo de caracteres inválidos (para Windows)
    invalid_chars = '<>:"/\\|?*'
    for c in invalid_chars:
        file_name = file_name.replace(c, '')
        
    file_path = os.path.join(curso_dir, file_name)
    
    print(f"Baixando: {file_name} -> {curso_dir}")
    
    fh = io.FileIO(file_path, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    
    try:
        while done is False:
            status, done = downloader.next_chunk()
        return file_path
    except Exception as e:
        print(f"Erro ao baixar o arquivo '{file_name}': {e}")
        fh.close()
        if os.path.exists(file_path):
            os.remove(file_path)
        return None
    finally:
        if not fh.closed:
            fh.close()
