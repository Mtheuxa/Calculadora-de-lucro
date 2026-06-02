import sys
from auth import get_drive_service

def list_contents(service, folder_id, depth=0, max_depth=3):
    if depth > max_depth: return
    query = f"'{folder_id}' in parents and trashed = false"
    
    results = service.files().list(
        q=query, 
        fields="files(id, name, mimeType, modifiedTime)", 
        pageSize=5,
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()
    items = results.get('files', [])
    
    for item in items:
        indent = "  " * depth
        tipo = "PASTA" if item['mimeType'] == 'application/vnd.google-apps.folder' else "ARQUIVO"
        print(f"{indent}- [{tipo}] {item['name']} (Data: {item.get('modifiedTime', '')[:10]})")
        
        if tipo == "PASTA":
            list_contents(service, item['id'], depth+1, max_depth)

def main():
    service = get_drive_service()
    if not service:
        print("Serviço indisponível.")
        return
        
    root_id = '1r6RrEwWSIK0Md00EKdccr8l_3C5dM-WY'
    try:
        folder = service.files().get(
            fileId=root_id, 
            fields="name",
            supportsAllDrives=True
        ).execute()
        print(f"\n--- ESTRUTURA DA PASTA RAIZ: {folder.get('name')} ---")
        list_contents(service, root_id, depth=1, max_depth=3)
    except Exception as e:
        print(f"Erro ao acessar a pasta raiz: {e}")

if __name__ == '__main__':
    main()
