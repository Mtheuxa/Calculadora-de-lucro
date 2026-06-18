import os
import sys
import re
from drive_service import DriveService

# Força o terminal a usar UTF-8 para não dar erro com caracteres especiais
sys.stdout.reconfigure(encoding='utf-8')

# --- CONFIGURAÇÕES A SEREM PREENCHIDAS PELO USUÁRIO ANTES DE RODAR ---
SOURCE_DRIVE_FOLDER_ID = "1CCAfj2zR02OVB6ZK8aKDSswSWWgN9d0Z" 
DESTINATION_DRIVE_FOLDER_ID = "1_vDYOk1VpGz6b2KgjeQrQUaHwmKtYmbX" # Pode deixar vazio se for criar tudo na raiz do seu Drive atual, ou colocar o ID de uma pasta vazia

# Coloque aqui o nome exato das pastas de cursos que quer processar. Ex: ["Biomedicina", "FARM Atual -Nylza"]
# Se deixar vazio [], ele vai varrer a universidade inteira (o que pode levar horas).
CURSOS_PERMITIDOS = ["Administração"]
# ----------------------------------------------------------------------

def extract_metadata(logical_path, file_name):
    """
    Exemplo de logical_path:
    "Biomedicina/Planos de Ensino/SEMIPRESENCIAL/1º PERÍODO/Plano de ensino - Bioestatística.pdf"
    "Biomedicina/Controle de UA/EAD/Controle de UA - Matemática 2025.2.pdf"
    """
    parts = logical_path.split('/')
    if len(parts) < 3:
        return None  # Não tem a profundidade esperada
        
    curso = parts[0]
    categoria = parts[1] # "Planos de Ensino", "Controle de UA", etc
    
    # Ignorar lixo ou pastas que não sejam de Planos ou UA
    if "plano" not in categoria.lower() and "ua" not in categoria.lower():
        return None

    # Filtrar rigidamente pelo nome do arquivo: SÓ aceita se o NOME tiver Plano de Ensino ou Controle de UA
    if not re.search(r"(?i)(plano de ensino|controle de ua)", file_name):
        return None

    # Tentar encontrar a modalidade (EAD, SEMIPRESENCIAL, etc)
    modalidade = "GERAL"
    for part in parts[2:]:
        if part.upper() in ["EAD", "SEMIPRESENCIAL", "PRESENCIAL", "FLEX", "HIBRIDO"]:
            modalidade = part.upper()
            break
            
    # Extrair Período (Ex: "1º Período", "2ºP", "3° P")
    periodo = "PERÍODO INDEFINIDO"
    for part in parts:
        match_periodo = re.search(r"(?i)(\d+)\s*[º°a-z]*\s*(período|p\b|entrada)", part)
        if match_periodo:
            periodo = f"{match_periodo.group(1)}º Período"
            break

    # Extrair Disciplina do nome do arquivo
    # Remove extensão
    name_no_ext = os.path.splitext(file_name)[0]
    
    # Limpeza básica do nome
    # Ex: "Plano de ensino - Anatomia sistêmica (1)" -> "Anatomia sistêmica"
    # Ex: "Controle de UA_Matemática_2026.1" -> "Matemática"
    
    # Remover prefixos comuns
    clean_name = re.sub(r"(?i)^(Plano de ensino|Controle de UA)\s*[-_–]?\s*", "", name_no_ext)
    
    # Remover (1), (2), etc
    clean_name = re.sub(r"\(\d+\)", "", clean_name)
    
    # Se quiser pegar só a disciplina e ignorar 2026.1 no nome para poder agrupar:
    # A disciplina será o clean_name, mas vamos guardar a string inteira para comparar depois e pegar a mais nova
    disciplina = clean_name.strip()
    
    # Vamos considerar que o que sobrou é a disciplina (ela pode conter " 2025.2" no fim)
    # Retornamos os dados extraídos
    return {
        "curso": curso,
        "categoria": categoria,
        "modalidade": modalidade,
        "periodo": periodo,
        "disciplina_bruta": disciplina,
        "ano_semestre": extract_year_semester(file_name + logical_path),
        "file_name": file_name
    }

def extract_year_semester(text):
    """Procura por 2025.1, 2026.1, 2026.2 etc no texto e retorna como float para facilitar comparação (2026.1 > 2025.2)"""
    match = re.search(r"20\d{2}\.[1-2]", text)
    if match:
        return float(match.group())
    return 0.0

def process_directory(source_id, dest_id, drive_service, allowed_courses=None, dry_run=True):
    print(f"Lendo arquivos da pasta de origem (ID: {source_id})... Isso pode levar um tempo.")
    
    # Dicionário para agrupar: chave = (curso, disciplina_limpa, modalidade, categoria)
    # Valor = lista de arquivos para ordenar
    grouped_files = {}
    
    for file_info in drive_service.walk_folder(source_id, allowed_root_folders=allowed_courses):
        file_id = file_info['id']
        file_name = file_info['name']
        logical_path = file_info['path']
        
        meta = extract_metadata(logical_path, file_name)
        if meta:
            # Para agrupar as disciplinas mesmo se uma for "Matemática 2025.2" e a outra "Matemática 2026.1"
            # Precisamos limpar o ano do nome da disciplina para ser a mesma chave
            disc_limpa = re.sub(r"20\d{2}\.[1-2]", "", meta["disciplina_bruta"]).strip()
            
            key = (meta["curso"], meta["periodo"], disc_limpa, meta["modalidade"], meta["categoria"])
            
            if key not in grouped_files:
                grouped_files[key] = []
            
            grouped_files[key].append({**meta, "id": file_id})
                
    if not grouped_files:
        print("Nenhum arquivo válido encontrado para processamento.")
        return

    print(f"\nIniciando organização dos arquivos...")
    
    if dry_run:
        print("MODO DRY-RUN (SIMULAÇÃO): As cópias não serão realmente feitas.\n")
        
    for key, files_list in grouped_files.items():
        # Ordenar os arquivos dessa disciplina/categoria do mais novo para o mais velho (maior ano/semestre primeiro)
        files_list.sort(key=lambda x: x["ano_semestre"], reverse=True)
        
        for index, file_data in enumerate(files_list):
            curso = file_data["curso"]
            periodo = key[1]
            disciplina = key[2] # A disciplina sem o ano
            modalidade = file_data["modalidade"]
            file_name = file_data["file_name"]
            file_id = file_data["id"]
            
            # O arquivo mais recente (index 0) vai para a pasta raiz da Modalidade
            if index == 0:
                path_list = [curso, periodo, disciplina, modalidade]
                status = "ATUAL"
            # Os desatualizados vão para a subpasta "Arquivos Antigos"
            else:
                path_list = [curso, periodo, disciplina, modalidade, "Arquivos Antigos"]
                status = "ANTIGO"
            
            print(f"[{status}] {file_name}")
            print(f"   -> {' > '.join(path_list)} > {file_name}")
            
            if not dry_run:
                # Cria/Pega ID da pasta final
                final_folder_id = drive_service.create_path(path_list, dest_id)
                # Faz a cópia
                drive_service.copy_file(file_id, file_name, final_folder_id)

if __name__ == '__main__':
    print("=== Automação de Google Drive API ===")
    
    if SOURCE_DRIVE_FOLDER_ID == "COLOQUE_AQUI_O_ID_DA_PASTA_RAIZ_DE_ORIGEM":
        print("AVISO: Você precisa colocar o ID da pasta de origem em SOURCE_DRIVE_FOLDER_ID no main.py!")
    else:
        try:
            drive_srv = DriveService()
            # Se DESTINATION_DRIVE_FOLDER_ID estiver vazio, as pastas (Cursos) serão criadas na "Meu Drive"
            root_dest = DESTINATION_DRIVE_FOLDER_ID if DESTINATION_DRIVE_FOLDER_ID else None
            
            # Altere dry_run para False para fazer a execução real!
            allowed = CURSOS_PERMITIDOS if CURSOS_PERMITIDOS else None
            process_directory(SOURCE_DRIVE_FOLDER_ID, root_dest, drive_srv, allowed_courses=allowed, dry_run=False)
            
        except Exception as e:
            print(f"Erro: {e}")
