import time

def list_items_in_folder(service, folder_id, is_folder=None):
    """Busca itens dentro de uma pasta específica. is_folder=True retorna só pastas, False retorna só arquivos."""
    items = []
    page_token = None
    
    query = f"'{folder_id}' in parents and trashed = false"
    if is_folder is True:
        query += " and mimeType = 'application/vnd.google-apps.folder'"
    elif is_folder is False:
        query += " and mimeType != 'application/vnd.google-apps.folder'"
        
    while True:
        try:
            results = service.files().list(
                q=query,
                spaces='drive',
                corpora='allDrives',
                fields="nextPageToken, files(id, name, mimeType, modifiedTime)",
                pageSize=100,
                pageToken=page_token,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            
            items.extend(results.get('files', []))
            page_token = results.get('nextPageToken')
            if not page_token:
                break
        except Exception as e:
            print(f"Erro ao listar itens da pasta {folder_id}: {e}")
            time.sleep(2) # Pausa pequena antes de desistir
            break
            
    return items

def extract_files_recursive(service, folder_id, curso_nome, limit_year=2026):
    """Navega recursivamente em subpastas e extrai todos os arquivos que atendam ao limite de ano."""
    arquivos_encontrados = []
    
    # Pega todos os arquivos desta pasta
    arquivos = list_items_in_folder(service, folder_id, is_folder=False)
    for arq in arquivos:
        mod_time = arq.get('modifiedTime', '')
        # Checa se o arquivo é do ano desejado (ou mais recente)
        # mod_time format: "2026-01-01T10:00:00Z"
        if mod_time >= f"{limit_year}-01-01T00:00:00":
            arq['curso'] = curso_nome
            arquivos_encontrados.append(arq)
            
    # Pega subpastas e entra nelas
    subpastas = list_items_in_folder(service, folder_id, is_folder=True)
    for sub in subpastas:
        arquivos_encontrados.extend(extract_files_recursive(service, sub['id'], curso_nome, limit_year))
        
    return arquivos_encontrados

def search_updated_files(service):
    """
    Nova lógica:
    1. Acha a pasta raiz 'Cursos NEAD'
    2. Lista os Cursos (subpastas)
    3. Busca as pastas 'Controle de UA' e 'Planos de Ensino' dentro de cada curso
    4. Varre os arquivos lá dentro.
    """
    arquivos_finais = []
    
    # 1. A raiz é diretamente o ponto de entrada.
    # Vamos usar o ID do Drive Compartilhado que você enviou.
    # A API às vezes recusa o "get" para Drives Compartilhados, então
    # vamos direto listar o que tem dentro (que já são os cursos).
    raiz_id = '1r6RrEwWSIK0Md00EKdccr8l_3C5dM-WY'
    
    print("Acessando a raiz do Drive (Cursos)...")
    cursos = list_items_in_folder(service, raiz_id, is_folder=True)
    
    # Se falhar no ID do Drive compartilhado, tenta no "Meu Drive" pessoal
    if not cursos:
        print("Não achou no ID compartilhado. Tentando no 'Meu Drive' padrão...")
        raiz_id = 'root'
        cursos = list_items_in_folder(service, raiz_id, is_folder=True)
        
    if not cursos:
        print("Erro: Não encontrei as pastas dos cursos na raiz do Drive.")
        return []

    # 2. Lista os Cursos
    cursos = list_items_in_folder(service, raiz_id, is_folder=True)
    print(f"Encontrados {len(cursos)} cursos/pastas na raiz.")
    
    # 3. Varre cada curso
    for curso in cursos:
        #print(f"Verificando curso: {curso['name']}...")
        subpastas_curso = list_items_in_folder(service, curso['id'], is_folder=True)
        
        for subpasta in subpastas_curso:
            nome_sub = subpasta['name'].lower()
            
            # Se for Controle de UA ou Plano de Ensino, entra para extrair os arquivos!
            if 'controle de ua' in nome_sub or 'plano de ensino' in nome_sub:
                print(f"-> Varrendo: {curso['name']} / {subpasta['name']}")
                
                # Coleta arquivos recursivamente (entra em 1º periodo, 2º periodo, etc)
                # O ANO LIMITE ESTÁ CONFIGURADO AQUI: 2026.
                arquivos = extract_files_recursive(service, subpasta['id'], curso_nome=curso['name'], limit_year=2026)
                arquivos_finais.extend(arquivos)

    print(f"\nBusca concluída! Total de arquivos de 2026 encontrados dentro das pastas alvo: {len(arquivos_finais)}")
    return arquivos_finais
