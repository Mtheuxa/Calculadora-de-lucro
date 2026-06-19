import os
import sys
import re
from drive_service import DriveService

# Força o terminal a usar UTF-8 para não dar erro com caracteres especiais
sys.stdout.reconfigure(encoding='utf-8')

# --- CONFIGURAÇÕES A SEREM PREENCHIDAS PELO USUÁRIO ANTES DE RODAR ---
SOURCE_DRIVE_FOLDER_ID = "1PF6v9AlWKlMHaTChaL2qUJnL2Yil9AMR" # COLOQUE AQUI O ID DA PASTA DO CURSO NO DRIVE
DESTINATION_DRIVE_FOLDER_ID = "1_vDYOk1VpGz6b2KgjeQrQUaHwmKtYmbX" # Pode deixar vazio se for criar tudo na raiz do seu Drive atual, ou colocar o ID de uma pasta vazia

# Coloque abaixo o nome do curso que deseja que seja o nome da pasta principal gerada.
# Ex: "Administração", "Biomedicina", etc.
NOME_DO_CURSO_FONTE = "CST Gestão em Tecnologia da Informação"
# ----------------------------------------------------------------------

def extract_metadata(logical_path, file_name, file_id=None, drive_service=None, course_name=None):
    """
    Extrai metadados do arquivo baseando-se no caminho e no nome do arquivo.
    Funciona tanto com estruturas rígidas (Curso/Categoria/Modalidade/Período) 
    quanto estruturas mais livres (apenas a pasta do período e nome do arquivo).
    """
    if not file_name.lower().endswith('.pdf'):
        return None

    parts = logical_path.split('/')
    
    # 1. Definir o Curso
    if course_name:
        curso = course_name
    else:
        if len(parts) < 2:
            return None
        curso = parts[0]
        
    # 2. Definir a Categoria (Plano de Ensino ou Controle de UA)
    full_path_str = logical_path + "/" + file_name
    
    is_plano = re.search(r"(?i)(plano de ensino|pe_|\bpe\b|pl\s*ens|plan\s*ens)", full_path_str)
    is_ua = re.search(r"(?i)(controle de ua|ua_|\bua\b)", full_path_str)
    
    if is_ua:
        categoria = "Controle de UA"
    elif is_plano:
        categoria = "Planos de Ensino"
    else:
        # Se não tiver a tag explícita, como todos os uploads agora são apenas PDF das disciplinas,
        # assumimos por padrão que seja Plano de Ensino em vez de descartar.
        categoria = "Planos de Ensino"

    # 3. Extrair Modalidade
    modalidade = "GERAL"
    for part in parts + [file_name]:
        for mod in ["EAD", "SEMIPRESENCIAL", "PRESENCIAL", "FLEX", "HIBRIDO"]:
            if re.search(fr"(?i)\b{mod}\b", part):
                modalidade = mod.upper()
                break
        if modalidade != "GERAL":
            break
            
    # 4. Extrair Período
    periodo = "PERÍODO INDEFINIDO"
    for part in parts + [file_name]:
        match_periodo = re.search(r"(?i)(\d+)\s*[º°a-z]*\s*(per\S*odo|p\b|entrada)", part)
        if match_periodo:
            periodo = f"{match_periodo.group(1)}º Período"
            break

    # 5. Extrair Disciplina do nome do arquivo
    name_no_ext = os.path.splitext(file_name)[0]
    
    # Remover prefixos comuns do nome
    clean_name = name_no_ext
    clean_name = re.sub(r"(?i)^(\(\d{4}\.\d\)\s*)?(Plano de ensino|Controle de UA|PE|Pl\s*Ens|Plan\s*Ens)\s*[-_–]?\s*", "", clean_name)
    clean_name = re.sub(r"\(\d+\)", "", clean_name)
    
    disciplina = clean_name.strip()
    
    return {
        "curso": curso,
        "categoria": categoria,
        "modalidade": modalidade,
        "periodo": periodo,
        "disciplina_bruta": disciplina,
        "ano_semestre": extract_year_semester(file_name + logical_path, file_id, drive_service, file_name),
        "file_name": file_name
    }

def extract_year_semester(text, file_id=None, drive_service=None, file_name=""):
    """Procura por 2025.1, 2026.1, 2026.2 etc no texto. Lê PDF se necessário."""
    match = re.search(r"20\d{2}\.[1-2]", text)
    if match:
        return float(match.group())
        
    if file_id and drive_service and file_name.lower().endswith('.pdf'):
        try:
            print(f"Lendo conteúdo interno do PDF: {file_name} para buscar data...")
            pdf_bytes = drive_service.download_file_to_memory(file_id)
            if pdf_bytes:
                import PyPDF2
                reader = PyPDF2.PdfReader(pdf_bytes)
                for i in range(min(3, len(reader.pages))):
                    page_text = reader.pages[i].extract_text()
                    if page_text:
                        match_pdf = re.search(r"20\d{2}\.[1-2]", page_text)
                        if match_pdf:
                            return float(match_pdf.group())
        except Exception as e:
            pass
            
    return 0.0

def process_directory(source_id, dest_id, drive_service, allowed_courses=None, dry_run=True, course_name=None):
    print(f"Lendo arquivos da pasta de origem (ID: {source_id})... Isso pode levar um tempo.")
    
    # Dicionário para agrupar: chave = (curso, disciplina_limpa, modalidade, categoria)
    # Valor = lista de arquivos para ordenar
    grouped_files = {}
    
    for file_info in drive_service.walk_folder(source_id, allowed_root_folders=allowed_courses):
        file_id = file_info['id']
        file_name = file_info['name']
        logical_path = file_info['path']
        
        meta = extract_metadata(logical_path, file_name, file_id, drive_service, course_name)
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
        
        # Pega apenas o MAIS RECENTE (index 0), ignorando totalmente os velhos
        file_data = files_list[0]
        
        curso = file_data["curso"]
        periodo = key[1]
        disciplina = key[2] # A disciplina sem o ano
        modalidade = file_data["modalidade"]
        file_name = file_data["file_name"]
        file_id = file_data["id"]
        
        path_list = [curso, periodo]
            
        status = "ATUAL"
        
        print(f"[{status}] {file_name}")
        print(f"   -> {' > '.join(path_list)} > {file_name}")
            
        if not dry_run:
            # Cria/Pega ID da pasta final
            final_folder_id = drive_service.create_path(path_list, dest_id)
            # Faz a cópia
            drive_service.copy_file(file_id, file_name, final_folder_id)

if __name__ == '__main__':
    print("=== Automação de Google Drive API ===")
    
    if not SOURCE_DRIVE_FOLDER_ID or SOURCE_DRIVE_FOLDER_ID == "COLOQUE_AQUI_O_ID_DA_PASTA_RAIZ_DE_ORIGEM":
        print("AVISO: Você precisa colocar o ID da pasta de origem em SOURCE_DRIVE_FOLDER_ID no main.py!")
    else:
        try:
            drive_srv = DriveService()
            # Se DESTINATION_DRIVE_FOLDER_ID estiver vazio, as pastas (Cursos) serão criadas na "Meu Drive"
            root_dest = DESTINATION_DRIVE_FOLDER_ID if DESTINATION_DRIVE_FOLDER_ID else None
                
            print(f"Iniciando leitura para a pasta do curso: {NOME_DO_CURSO_FONTE}")
            
            # Altere dry_run para False para fazer a execução real!
            process_directory(SOURCE_DRIVE_FOLDER_ID, root_dest, drive_srv, allowed_courses=None, dry_run=False, course_name=NOME_DO_CURSO_FONTE)
            
        except Exception as e:
            print(f"Erro: {e}")
